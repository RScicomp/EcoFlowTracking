#!/usr/bin/env python3
"""
Wait for EcoFlow device to come online
"""

import os
import requests
import hashlib
import hmac
import random
import binascii
import time
from dotenv import load_dotenv

def get_qstr(params):
    """Generate query string from parameters"""
    if not params:
        return ""
    return '&'.join([f"{key}={params[key]}" for key in sorted(params.keys())])

def hmac_sha256(data: str, key: str) -> str:
    """Generate HMAC-SHA256 signature"""
    hashed = hmac.new(key.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).digest()
    return binascii.hexlify(hashed).decode('utf-8')

def get_map(json_obj, prefix=""):
    """Flatten JSON object for signature generation"""
    def flatten(obj, pre=""):
        result = {}
        if isinstance(obj, dict):
            for k, v in obj.items():
                result.update(flatten(v, f"{pre}.{k}" if pre else k))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                result.update(flatten(item, f"{pre}[{i}]"))
        else:
            result[pre] = obj
        return result
    return flatten(json_obj, prefix)

def check_device_status():
    """Check if the target device is online"""
    load_dotenv()
    
    access_key = os.getenv('ECOFLOW_ACCESS_KEY')
    secret_key = os.getenv('ECOFLOW_SECRET_KEY')
    device_sn = os.getenv('ECOFLOW_DEVICE_SN')
    
    if not all([access_key, secret_key, device_sn]):
        print("❌ Missing environment variables")
        return False, None
    
    base_url = "https://api.ecoflow.com"
    
    try:
        params = {
            "sn": device_sn
        }
        
        nonce = str(random.randint(100000, 999999))
        timestamp = str(int(time.time() * 1000))
        headers = {
            'accessKey': access_key,
            'nonce': nonce,
            'timestamp': timestamp
        }
        
        sign_str = (get_qstr(get_map(params)) + '&' if params else '') + get_qstr(headers)
        headers['sign'] = hmac_sha256(sign_str, secret_key)
        
        response = requests.get(f"{base_url}/iot-open/sign/device/list", headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                devices = data.get('data', [])
                for device in devices:
                    if device.get('sn') == device_sn:
                        online = device.get('online', 0)
                        product_name = device.get('productName', 'Unknown')
                        return online == 1, product_name
        return False, None
        
    except Exception as e:
        print(f"❌ Error checking device status: {e}")
        return False, None

def wait_for_device():
    """Wait for device to come online"""
    print("🔍 Waiting for EcoFlow device to come online...")
    print("=" * 50)
    
    check_count = 0
    while True:
        check_count += 1
        is_online, product_name = check_device_status()
        
        timestamp = time.strftime("%H:%M:%S")
        
        if is_online:
            print(f"[{timestamp}] ✅ Device is ONLINE! ({product_name})")
            print("🎉 Your EcoFlow monitoring system should now work!")
            print("\nYou can now:")
            print("1. Start the monitor: python ecoflow_monitor.py")
            print("2. Generate a dashboard: python dashboard_generator.py")
            print("3. Run diagnostics: python diagnostic.py")
            break
        else:
            print(f"[{timestamp}] ⏳ Device is offline... (check #{check_count})")
            print("   Make sure your device is:")
            print("   - Powered on")
            print("   - Connected to WiFi")
            print("   - Visible in the EcoFlow app")
            print()
        
        # Wait 30 seconds before next check
        time.sleep(30)

if __name__ == "__main__":
    wait_for_device() 