import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
# import os
# import re

# base_dir = "/Users/rasheltublin/Desktop/Hoopo/ZIM pilot/newPV battery report"

def detect_date_format(date_series):
    for fmt in ["%Y-%m-%d %H:%M:%S.%f",'%d/%m/%Y %H:%M','%m/%d/%Y %H:%M']:
        try:
            pd.to_datetime(date_series, format=fmt)
            return fmt
        except ValueError: 
            continue
    return None

def extract_voltage_fport1(payload_col): # vectorized extract voltage
    return payload_col.str.extract(r'Battery Level (\d+\.\d+)', expand=False)

def extract_power_mode(payload_col):
    return payload_col.str.extract(r'Power mode (\w+)', expand=False).fillna('None')

def get_ready_latest_batt(latest_batt):
    latest_batt['Voltage'] = extract_voltage_fport1(latest_batt['PayloadData'])
    latest_batt['Voltage'] = pd.to_numeric(latest_batt['Voltage'], errors='coerce')
    non_numeric_rows = latest_batt[latest_batt['Voltage'].isna()]
    if non_numeric_rows.empty:
        print('All rows have a numeric value for Voltage.')
    else:
        print("Some rows had non-numeric values for Voltage, see these in variable 'non_numeric_rows', cleaned.")
        latest_batt = latest_batt[~latest_batt['Voltage'].isna()]

    fmt = detect_date_format(latest_batt['EventTimeUTC'])
    latest_batt['EventTimeUTC'] = pd.to_datetime(latest_batt['EventTimeUTC'], format=fmt)
    print('EventTimeUTC is in DateTime-format.')

    crit_level = 3.18
    
    latest_batt['PowerMode'] = extract_power_mode(latest_batt['PayloadData'])
    wrong_labels = list(set(latest_batt['PowerMode'].unique()) - set(['High', 'Medium', 'Low', 'Critical']))
    mask = latest_batt['PowerMode'].isin(wrong_labels)
    print(f"There are {len(latest_batt[mask])} trackers out of {len(latest_batt)} paired trackers which don't have a well-defined 'Power mode' in the payload data but instead have:")
    print(wrong_labels)

    conditions = [
        (latest_batt.loc[mask,'Voltage'] > 3.3),
        (latest_batt.loc[mask,'Voltage'] > 3.22) & (latest_batt.loc[mask,'Voltage'] <= 3.3),
        (latest_batt.loc[mask,'Voltage'] > crit_level) & (latest_batt.loc[mask,'Voltage'] <= 3.22),
        (latest_batt.loc[mask,'Voltage'] <= crit_level)
    ]
    modes = np.array(['High', 'Medium', 'Low', 'Critical'], dtype=str)
    
    latest_batt.loc[mask, 'PowerMode'] = np.select(conditions, modes, default='Unknown')
    
    print(f"Added 'Power mode' for the ones with wrong/no labels under the same definitions (with critical at {crit_level}).")
    
    return latest_batt

def is_6000(ID):
    if len(ID) < 4 or not ID[-4:].isdigit():
        return False
    return int(ID[-4:]) >= 6000

def create_snapshot_chart(latest_batt, IDs_list, report_date, paired=True, list_name='', path_save = None):

    if path_save is None:
        # base_dir = "/Users/rasheltublin/Desktop/Hoopo/ZIM pilot/newPV battery report"
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"latest_batt_reports/charts/snapshot_{report_date.replace(' ', '')}_{timestamp}.png"  # Add timestamp to filename
        # path_save = os.path.join(base_dir, filename)
        path_save = filename
    
    order = ['Critical','Low','Medium','High']
    palette = {
        'High': 'tab:green',
        'Medium': 'tab:blue',
        'Low': 'tab:orange',
        'Critical': 'tab:red'
    }

    if paired:
        cond_paired = (latest_batt['DeviceID'] != latest_batt['DeviceName'])
        df = latest_batt[(latest_batt['DeviceID'].isin(IDs_list)) & cond_paired]
        # print(f"As of {report_date} there are {len(df)} paired trackers in this list.")
    else:
        df = latest_batt[latest_batt['DeviceID'].isin(IDs_list)]
        # print(f"As of {report_date} there are {len(df)} trackers in this list paired & unpaired.")
    
    
    plt.figure(figsize=(4, 6))
    ax = sns.countplot(data=df, x='PowerMode', hue='PowerMode', order=order, palette=palette)
    try:
        ax.get_legend().remove()
    except:
        pass  # No legend to remove
    
    for p in ax.patches:
        height = p.get_height()
        ax.text(p.get_x() + p.get_width() / 2., height+len(df)/500,
                f'{round(int(height)/len(df)*100,2)}%', ha="center")
    
    ax = plt.gca() 
    ax.set_yticks([])
    ax.set_yticklabels([])
    
    plt.xlabel('Power Zone')
    plt.ylabel('Trackers per Power Zone')
    plt.title(f"Tracker Battery Power Zones\n{list_name} ({len(df)}) devices\nSnapshot of {report_date}")
    
    plt.tight_layout()
    plt.savefig(path_save)
    plt.close()

    return path_save

if __name__ == "__main__":
   create_snapshot_chart()