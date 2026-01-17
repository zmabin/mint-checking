#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import time
import os
from datetime import datetime

BEARER_TOKEN = os.environ.get('BEARER_TOKEN', '')

print("=" * 60)
print("🔍 调试信息")
print("=" * 60)
print(f"Token是否存在: {'是' if BEARER_TOKEN else '否'}")
print(f"Token长度: {len(BEARER_TOKEN)}")
print(f"Token前20位: {BEARER_TOKEN[:20]}...")
print(f"Token后20位: ...{BEARER_TOKEN[-20:]}")
print("=" * 60)

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
        url = f"{BASE_URL}/api/user/info"
        log(f"🔍 请求URL: {url}")
        
        r = requests.get(url, headers=HEADERS, timeout=10)
        
        log(f"📡 状态码: {r.status_code}")
        log(f"📄 响应头: {dict(r.headers)}")
        log(f"📝 响应内容: {r.text}")
        
        if r.status_code == 200:
            return r.json()
        else:
            log(f"❌ 请求失败")
            return None
    except Exception as e:
        log(f"❌ 异常: {type(e).__name__}: {e}")
        import traceback
        log(f"📋 详细错误:\n{traceback.format_exc()}")
        return None

def main():
    log("🎰 开始执行")
    
    user = get_user_info()
    if not user:
        log("❌ 无法获取用户信息")
        return
    
    log(f"✅ 成功获取用户信息")
    log(f"👤 用户: {user.get('username')} | 💰 余额: {user.get('balance')}")

if __name__ == "__main__":
    main()
