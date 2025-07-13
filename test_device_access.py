#!/usr/bin/env python3
"""
Test script to check device access and list available devices
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

def test_device_access():
    """Test access to the specific device"""
    load_dotenv()
    
    access_key = os.getenv('ECOFLOW_ACCESS_KEY')
    secret_key = os.getenv('ECOFLOW_SECRET_KEY')
    device_sn = os.getenv('ECOFLOW_DEVICE_SN')
    
    if not all([access_key, secret_key, device_sn]):
        print("❌ Missing environment variables")
        return False
    
    base_url = "https://api.ecoflow.com"
    
    print(f"Testing access to device: {device_sn}")
    print("=" * 50)
    
    # Test 1: Try to get device info
    try:
        print("1. Testing device info endpoint...")
        
        # Try a different endpoint that might work
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
        
        # Try device list endpoint
        response = requests.get(f"{base_url}/iot-open/sign/device/list", headers=headers, params=params)
        print(f"   Device list status: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print("✅ Device list API working")
                devices = data.get('data', {}).get('devices', [])
                print(f"   Found {len(devices)} devices:")
                for device in devices:
                    sn = device.get('sn', 'Unknown')
                    name = device.get('deviceName', 'Unknown')
                    print(f"     - {name} ({sn})")
                    if sn == device_sn:
                        print(f"       ✅ This matches your configured device SN")
                    else:
                        print(f"       ⚠️  This is different from your configured device SN")
                return True
            else:
                print(f"❌ API error: {data.get('message', 'Unknown error')}")
        else:
            print(f"❌ HTTP error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Try different device SN formats
    print("\n2. Testing different device SN formats...")
    
    # Try without the "R" prefix
    if device_sn.startswith('R'):
        alt_sn = device_sn[1:]
        print(f"   Trying without 'R' prefix: {alt_sn}")
        
        params = {
            "sn": alt_sn,
            "params": {
                "quotas": ["pd.soc"]
            }
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
        
        response = requests.post(f"{base_url}/iot-open/sign/device/quota", headers=headers, json=params)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print("✅ Alternative device SN format works!")
                return True
            else:
                print(f"❌ Still getting error: {data.get('message', 'Unknown error')}")
    
    # Test 3: Check if device is online
    print("\n3. Checking device online status...")
    print("   The 'no permission to do it' error usually means:")
    print("   - Device is offline or not connected to the internet")
    print("   - Device SN doesn't match your API account")
    print("   - API account doesn't have permission for this device")
    print("   - Device needs to be registered with your EcoFlow account")
    
    return False

if __name__ == "__main__":
    test_device_access() 