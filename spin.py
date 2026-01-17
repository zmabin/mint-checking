#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import time
import os
from datetime import datetime

BEARER_TOKEN = os.environ.get('BEARER_TOKEN', '')

if not BEARER_TOKEN:
    print("❌ 未设置 BEARER_TOKEN")
    exit(1)

BASE_URL = "https://up.x666.me"
HEADERS = {
    "accept": "*/*",
    "authorization": f"Bearer {BEARER_TOKEN}",
    "content-type": "application/json",
    "origin": BASE_URL,
    "referer": f"{BASE_URL}/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_user_info():
    try:
        r = requests.get(f"{BASE_URL}/api/user/info", headers=HEADERS, timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        log(f"❌ 错误: {e}")
        return None

def spin_wheel():
    try:
        r = requests.post(f"{BASE_URL}/api/checkin/spin", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get('success'):
                log(f"✅ {data.get('message')} | 获得: {data.get('times')} | 余额: {data.get('new_balance')}")
                return True, data.get('times', 0)
            else:
                log(f"⚠️ {data.get('message')}")
                return False, 0
        return False, 0
    except Exception as e:
        log(f"❌ 异常: {e}")
        return False, 0

def main():
    log("🎰 开始执行")
    
    user = get_user_info()
    if not user:
        log("❌ 无法获取用户信息")
        return
    
    log(f"👤 用户: {user.get('username')} | 💰 余额: {user.get('balance')}")
    
    total = 0
    count = 0
    
    for i in range(6):
        success, earned = spin_wheel()
        if success:
            total += earned
            count += 1
            time.sleep(2)
        else:
            break
    
    log(f"📊 完成！成功 {count} 次，获得 {total} 次")
    
    final = get_user_info()
    if final:
        log(f"💰 最终余额: {final.get('balance')}")

if __name__ == "__main__":
    main()
