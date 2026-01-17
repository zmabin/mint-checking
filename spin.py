#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import time
import os
import random
from datetime import datetime

# 环境变量
BEARER_TOKEN = os.environ.get('BEARER_TOKEN', '')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

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

def send_telegram(message):
    """发送Telegram通知"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log("⚠️ 未配置Telegram，跳过通知")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        r = requests.post(url, json=data, timeout=10)
        if r.status_code == 200:
            log("✅ Telegram通知发送成功")
            return True
        else:
            log(f"❌ Telegram通知失败: {r.status_code}")
            return False
    except Exception as e:
        log(f"❌ Telegram通知异常: {e}")
        return False

def get_user_info():
    """获取用户信息"""
    try:
        r = requests.get(f"{BASE_URL}/api/user/info", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get('success'):
                return data
        return None
    except Exception as e:
        log(f"❌ 错误: {e}")
        return None

def spin_wheel():
    """执行转盘"""
    try:
        r = requests.post(f"{BASE_URL}/api/checkin/spin", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get('success'):
                times = data.get('times', 0)
                message = data.get('message', '转盘成功')
                log(f"✅ {message} | 获得: {times} 次")
                return True, times
            else:
                log(f"⚠️ {data.get('message', '转盘失败')}")
                return False, 0
        else:
            log(f"❌ HTTP {r.status_code}")
            return False, 0
    except Exception as e:
        log(f"❌ 异常: {e}")
        return False, 0

def main():
    log("=" * 60)
    log("🎰 up.x666.me 自动转盘脚本")
    log("=" * 60)
    
    # 获取用户信息（验证token）
    user = get_user_info()
    if not user:
        error_msg = "❌ 无法获取用户信息，Token可能已过期！"
        log(error_msg)
        
        # 发送Telegram告警
        telegram_msg = f"""
🚨 <b>up.x666.me Token过期告警</b>

⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
❌ 状态: Token验证失败
📝 说明: 无法获取用户信息，请检查Token是否过期

🔧 解决方法:
1. 登录 up.x666.me
2. 获取新的Token
3. 更新GitHub Secret中的BEARER_TOKEN
"""
        send_telegram(telegram_msg)
        exit(1)
    
    username = user.get('username', 'Unknown')
    log(f"👤 用户: {username}")
    log(f"✅ Token验证成功")
    
    # 随机转盘次数（1-5次）
    spin_count = random.randint(1, 5)
    log(f"🎲 本次随机转盘次数: {spin_count}")
    
    # 开始转盘
    total_earned = 0
    success_count = 0
    
    for i in range(1, spin_count + 1):
        log(f"🎯 第 {i}/{spin_count} 次转盘...")
        success, earned = spin_wheel()
        
        if success:
            total_earned += earned
            success_count += 1
            
            # 如果不是最后一次，等待2-4秒（随机）
            if i < spin_count:
                wait_time = random.randint(2, 4)
                log(f"⏳ 等待 {wait_time} 秒...")
                time.sleep(wait_time)
        else:
            log("⏹️ 转盘失败，停止")
            break
    
    # 总结
    log("=" * 60)
    log("📊 转盘完成！")
    log(f"✅ 成功次数: {success_count}/{spin_count}")
    log(f"🎁 总共获得: {total_earned} 次")
    log("=" * 60)
    
    # 发送成功通知
    telegram_msg = f"""
✅ <b>up.x666.me 转盘完成</b>

👤 用户: {username}
⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🎲 转盘次数: {success_count}/{spin_count}
🎁 获得奖励: {total_earned} 次
"""
    send_telegram(telegram_msg)
    
    log("✨ 任务完成！")

if __name__ == "__main__":
    main()
