#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动刷新 up.x666.me 的 Bearer Token
通过 Playwright 自动化浏览器完成 Linux.do OAuth 登录流程
"""
import os
import sys
import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# 环境变量
LINUXDO_USERNAME = os.environ.get('LINUXDO_USERNAME', '')
LINUXDO_PASSWORD = os.environ.get('LINUXDO_PASSWORD', '')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# GitHub Actions 环境变量
GITHUB_ENV = os.environ.get('GITHUB_ENV', '')

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def send_telegram(message):
    """发送Telegram通知"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log("⚠️ 未配置Telegram，跳过通知")
        return False

    try:
        import requests
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

def send_telegram_photo(photo_path, caption=""):
    """发送截图到Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    if not os.path.exists(photo_path):
        return False

    try:
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        with open(photo_path, 'rb') as f:
            r = requests.post(url, data={
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": caption,
            }, files={"photo": f}, timeout=30)
        if r.status_code == 200:
            log("✅ Telegram截图发送成功")
            return True
        else:
            log(f"❌ Telegram截图发送失败: {r.status_code}")
            return False
    except Exception as e:
        log(f"❌ Telegram截图发送异常: {e}")
        return False

def get_new_token():
    """通过 Playwright 自动化获取新 token"""
    log("🚀 启动浏览器自动化...")

    with sync_playwright() as p:
        # 启动浏览器（使用真实浏览器特征绕过 Cloudflare）
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )

        # 创建上下文，模拟真实浏览器
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            extra_http_headers={
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
        )

        # 注入脚本隐藏自动化特征
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = {
                runtime: {}
            };
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)

        page = context.new_page()

        try:
            # 1. 访问 up.x666.me
            log("📍 访问 up.x666.me...")
            page.goto("https://up.x666.me", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(2)

            # 2. 点击登录按钮
            log("🔘 点击登录按钮...")
            login_btn = page.locator("button.login-btn, .login-btn, button:has-text('登录')")
            login_btn.click(timeout=10000)

            # 3. 等待跳转到 Linux.do OAuth 授权页面
            log("⏳ 等待跳转到 Linux.do...")
            page.wait_for_url("**linux.do**", timeout=15000)
            current_url = page.url
            log(f"📍 当前 URL: {current_url}")

            # 4. 等待 Cloudflare 验证完成 — 以 Discourse 登录表单出现为准
            log("⏳ 等待 Cloudflare 验证及页面加载...")
            login_form_locator = page.locator("input#login-account-name, input[name='login']").first
            try:
                login_form_locator.wait_for(state="visible", timeout=60000)
                log("✅ Cloudflare 验证通过，登录表单已加载")
            except PlaywrightTimeout:
                log("❌ 登录表单未出现，可能 Cloudflare 验证未通过")
                try:
                    page.screenshot(path="cloudflare_blocked.png")
                    log(f"📸 已保存截图，当前URL: {page.url}")
                    log(f"📄 页面标题: {page.title()}")
                    send_telegram_photo("cloudflare_blocked.png", f"Cloudflare 验证未通过\nURL: {page.url}")
                except:
                    pass
                return None

            # 5. 在 Linux.do 登录页面输入账号密码
            current_url = page.url
            log(f"📍 验证后 URL: {current_url}")
            if "linux.do" in current_url or "discourse" in current_url:
                log("🔐 检测到 Linux.do 登录页面，输入账号密码...")

                # 输入用户名
                login_form_locator.fill(LINUXDO_USERNAME)
                log(f"✅ 已输入用户名: {LINUXDO_USERNAME}")

                # 输入密码
                password_input = page.locator("input#login-account-password, input[name='password']").first
                password_input.fill(LINUXDO_PASSWORD)
                log("✅ 已输入密码")

                # 点击登录按钮
                submit_btn = page.locator("button#login-button").first
                submit_btn.click(timeout=10000)
                log("🔘 已点击登录按钮")

                # 等待登录完成 - URL应从 /login 跳转走
                try:
                    page.wait_for_url(
                        lambda url: "/login" not in url,
                        timeout=20000
                    )
                    log(f"✅ 登录成功，已跳转: {page.url}")
                except PlaywrightTimeout:
                    # 检查是否有登录错误提示
                    error_msg = ""
                    try:
                        error_el = page.locator(".alert-error, #modal-alert, .login-error").first
                        if error_el.is_visible(timeout=2000):
                            error_msg = error_el.text_content()
                    except:
                        pass
                    if error_msg:
                        log(f"❌ Linux.do 登录失败: {error_msg}")
                    else:
                        log(f"⚠️ 登录后未跳转，当前URL: {page.url}")
                    # 截图用于调试
                    try:
                        page.screenshot(path="login_failed.png")
                        log("📸 已保存登录失败截图")
                        send_telegram_photo("login_failed.png", f"Linux.do 登录失败\nURL: {page.url}")
                    except:
                        pass

                time.sleep(2)

            # 6. 处理 OAuth 授权页面（如果有）
            current_url = page.url
            log(f"📍 登录后 URL: {current_url}")

            if "x666.me" not in current_url and "/login" not in current_url:
                # 还没回调且不在登录页，可能在授权页面，尝试查找并点击授权按钮
                log("🔍 检查是否有授权按钮...")
                try:
                    authorize_btn = page.locator(
                        "button:has-text('授权'), button:has-text('Authorize'), "
                        "button:has-text('允许'), button:has-text('Allow')"
                    ).first
                    if authorize_btn.is_visible(timeout=5000):
                        log("🔐 检测到授权按钮，点击授权...")
                        authorize_btn.click(timeout=10000)
                        log("✅ 已点击授权按钮")
                        time.sleep(2)
                except:
                    log("ℹ️ 未检测到授权按钮，等待自动跳转...")

            # 7. 等待回调到 up.x666.me 并提取 token
            log("⏳ 等待回调...")
            page.wait_for_url("**x666.me**", timeout=30000)

            # 等待页面加载完成
            time.sleep(3)

            # 从 URL 参数或 localStorage 提取 token
            final_url = page.url
            log(f"📍 回调 URL: {final_url}")

            # 方法1: 从 URL 参数提取
            token_match = re.search(r'[?&]token=([^&]+)', final_url)
            if token_match:
                token = token_match.group(1)
                log(f"✅ 从 URL 提取到 token: {token[:20]}...")
                return token

            # 方法2: 从 localStorage 提取
            token = page.evaluate("() => localStorage.getItem('userToken')")
            if token:
                log(f"✅ 从 localStorage 提取到 token: {token[:20]}...")
                return token

            # 方法3: 等待并重试
            log("⏳ Token 未立即出现，等待 5 秒后重试...")
            time.sleep(5)
            token = page.evaluate("() => localStorage.getItem('userToken')")
            if token:
                log(f"✅ 从 localStorage 提取到 token: {token[:20]}...")
                return token

            log("❌ 未能提取到 token")
            return None

        except PlaywrightTimeout as e:
            log(f"❌ 超时错误: {e}")
            try:
                page.screenshot(path="timeout_screenshot.png")
                log(f"📸 已保存超时截图")
                log(f"📍 超时时URL: {page.url}")
                log(f"📄 页面标题: {page.title()}")
                send_telegram_photo("timeout_screenshot.png", f"超时错误\nURL: {page.url}\n标题: {page.title()}")
            except:
                pass
            return None
        except Exception as e:
            log(f"❌ 发生错误: {e}")
            # 截图用于调试
            try:
                screenshot_path = "error_screenshot.png"
                page.screenshot(path=screenshot_path)
                log(f"📸 已保存错误截图: {screenshot_path}")
                send_telegram_photo(screenshot_path, f"发生错误: {e}")
            except:
                pass
            return None
        finally:
            browser.close()

def main():
    log("=" * 60)
    log("🔄 up.x666.me Token 自动刷新脚本")
    log("=" * 60)

    # 检查必需的环境变量
    if not LINUXDO_USERNAME or not LINUXDO_PASSWORD:
        error_msg = "❌ 未设置 LINUXDO_USERNAME 或 LINUXDO_PASSWORD"
        log(error_msg)
        send_telegram(f"🚨 <b>Token刷新失败</b>\n\n{error_msg}")
        sys.exit(1)

    # 获取新 token
    new_token = get_new_token()

    if new_token:
        log("=" * 60)
        log("✅ Token 刷新成功！")
        log(f"🔑 新 Token: {new_token[:30]}...")
        log("=" * 60)

        # 如果在 GitHub Actions 中运行，输出到 GITHUB_ENV
        if GITHUB_ENV:
            try:
                with open(GITHUB_ENV, 'a') as f:
                    f.write(f"NEW_BEARER_TOKEN={new_token}\n")
                log("✅ 已将新 token 写入 GITHUB_ENV")
            except Exception as e:
                log(f"⚠️ 写入 GITHUB_ENV 失败: {e}")

        # 发送成功通知
        telegram_msg = f"""
✅ <b>up.x666.me Token 刷新成功</b>

⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔑 新Token: <code>{new_token[:30]}...</code>

📝 请手动更新 GitHub Secret 中的 BEARER_TOKEN
"""
        send_telegram(telegram_msg)

        # 输出到标准输出（方便手动运行时复制）
        print("\n" + "=" * 60)
        print("请复制以下 token 并更新到 GitHub Secrets:")
        print(new_token)
        print("=" * 60 + "\n")

    else:
        error_msg = "❌ Token 刷新失败"
        log(error_msg)

        telegram_msg = f"""
🚨 <b>up.x666.me Token 刷新失败</b>

⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
❌ 状态: 自动登录失败

🔧 可能的原因:
1. Linux.do 账号密码错误
2. 网站登录流程发生变化
3. 网络连接问题

请检查日志并手动更新 token。
"""
        send_telegram(telegram_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()
