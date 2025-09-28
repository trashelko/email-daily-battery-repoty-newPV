#!/usr/bin/env python3
"""
Test script to check SMBs database query and data processing.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.queries import get_latest_voltage
from data_processing.parsing import process_smbs_data
import pandas as pd

def test_smbs_query_and_processing():
    """Test the SMBs database query and data processing."""
    print("🔍 Testing SMBs database connection, query, and processing...")
    
    try:
        # Step 1: Test database query
        print("📊 Step 1: Fetching latest data from SMBs database...")
        latest_batt_raw, query_time = get_latest_voltage()
        
        print(f"✅ Query successful!")
        print(f"⏱️  Query time: {query_time:.2f} seconds")
        print(f"📈 Records returned: {len(latest_batt_raw)}")
        
        if len(latest_batt_raw) == 0:
            print("⚠️  No data returned from SMBs database")
            return False
        
        # Show raw data info
        print(f"\n📋 Raw data sample:")
        print(latest_batt_raw.sample(5))
        print(f"\n📊 Raw data types:")
        print(latest_batt_raw.dtypes)
        print(f"\n🔍 Raw column names:")
        print(list(latest_batt_raw.columns))
        
        # Step 2: Test data processing
        print(f"\n🔄 Step 2: Processing SMBs data...")
        latest_batt_processed = process_smbs_data(latest_batt_raw)
        
        print(f"✅ Processing successful!")
        print(f"📈 Processed records: {len(latest_batt_processed)}")
        
        # Show processed data info
        print(f"\n📋 Processed data sample:")
        print(latest_batt_processed.sample(5))
        print(f"\n📊 Processed data types:")
        print(latest_batt_processed.dtypes)
        print(f"\n🔍 Processed column names:")
        print(list(latest_batt_processed.columns))
        
        # Show PowerMode distribution
        if 'PowerMode' in latest_batt_processed.columns:
            print(f"\n⚡ PowerMode distribution:")
            print(latest_batt_processed['PowerMode'].value_counts())
            
        # Show voltage range
        if 'Voltage' in latest_batt_processed.columns:
            print(f"\n📊 Voltage statistics:")
            print(f"   Min: {latest_batt_processed['Voltage'].min():.2f}V")
            print(f"   Max: {latest_batt_processed['Voltage'].max():.2f}V")
            print(f"   Mean: {latest_batt_processed['Voltage'].mean():.2f}V")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"🔧 Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_smbs_query_and_processing()
    if success:
        print("\n🎉 SMBs query and processing test completed successfully!")
    else:
        print("\n💥 SMBs query and processing test failed!")
        sys.exit(1)
