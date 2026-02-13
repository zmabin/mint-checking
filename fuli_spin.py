#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import time
import os
import random
from datetime import datetime

# 环境变量
FULI_COOKIE = os.environ.get('FULI_COOKIE', '')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

if not FULI_COOKIE:
    print("❌ 未设置 FULI_COOKIE")
    exit(1)

BASE_URL = "https://fuli.hxi.me"
HEADERS = {
    "cookie": FULI_COOKIE,
    "origin": BASE_URL,
    "referer": f"{BASE_URL}/wheel",
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
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
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

def draw():
    """执行一次抽奖"""
    try:
        r = requests.post(f"{BASE_URL}/api/wheel", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            log(f"🎰 抽奖结果: {data}")
            return True, data
        else:
            log(f"❌ HTTP {r.status_code}: {r.text}")
            return False, None
    except Exception as e:
        log(f"❌ 异常: {e}")
        return False, None

def main():
    log("=" * 60)
    log("🎁 fuli.hxi.me 幸运转盘脚本")
    log("=" * 60)

    # 随机抽奖1-3次（截图显示每日2次机会，多试几次兜底）
    spin_count = random.randint(1, 3)
    log(f"🎲 本次计划抽奖次数: {spin_count}")

    results = []
    success_count = 0

    for i in range(1, spin_count + 1):
        log(f"🎯 第 {i}/{spin_count} 次抽奖...")
        success, data = draw()

        if success:
            results.append(data)
            success_count += 1
            if i < spin_count:
                wait_time = random.randint(2, 5)
                log(f"⏳ 等待 {wait_time} 秒...")
                time.sleep(wait_time)
        else:
            log("⏹️ 抽奖失败或次数用尽，停止")
            break

    log("=" * 60)
    log(f"📊 抽奖完成！成功 {success_count}/{spin_count} 次")
    log("=" * 60)

    # Telegram通知
    results_text = "\n".join([f"  第{i+1}次: {r}" for i, r in enumerate(results)])
    telegram_msg = f"""✅ <b>fuli.hxi.me 转盘完成</b>

⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🎲 抽奖次数: {success_count}/{spin_count}
📋 结果:
{results_text}"""
    send_telegram(telegram_msg)

    log("✨ 任务完成！")

if __name__ == "__main__":
    main()
