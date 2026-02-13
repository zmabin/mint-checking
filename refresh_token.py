#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动刷新 up.x666.me 的 Bearer Token
通过 DrissionPage 控制真实 Chrome 浏览器完成 Linux.do OAuth 登录流程
"""
import os
import sys
import time
import socket
from datetime import datetime
from DrissionPage import ChromiumPage, ChromiumOptions

# 环境变量
LINUXDO_USERNAME = os.environ.get('LINUXDO_USERNAME', '')
LINUXDO_PASSWORD = os.environ.get('LINUXDO_PASSWORD', '')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
CHROME_PATH = os.environ.get('CHROME_PATH', '')

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

def find_free_port(start=9222, end=9322):
    """在指定范围内查找可用端口"""
    for port in range(start, end + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return start

def find_browser_path():
    """自动检测 Chrome 浏览器路径"""
    if CHROME_PATH and os.path.exists(CHROME_PATH):
        return CHROME_PATH

    import platform
    system = platform.system()

    if system == 'Windows':
        candidates = [
            os.path.join(os.environ.get('ProgramFiles', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
            os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
            os.path.join(os.environ.get('LocalAppData', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        ]
    elif system == 'Darwin':
        candidates = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        ]
    else:  # Linux
        candidates = [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/opt/google/chrome/chrome',
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser',
        ]

    for path in candidates:
        if path and os.path.exists(path):
            return path

    # Linux: 尝试 which 命令
    if system == 'Linux':
        import shutil
        for cmd in ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']:
            found = shutil.which(cmd)
            if found:
                # 排除 snap 版本
                real_path = os.path.realpath(found)
                if '/snap' not in real_path:
                    return found

    return None

def wait_for_cf(page, timeout=120):
    """等待 Cloudflare 验证完成"""
    cf_markers = [
        "just a moment",
        "请稍候",
        "checking your browser",
        "cf-browser-verification",
    ]

    start = time.time()
    while time.time() - start < timeout:
        try:
            html = page.html.lower()
            if not any(marker in html for marker in cf_markers):
                return True

            log("⏳ Cloudflare 验证中...")

            # 尝试点击 Turnstile checkbox
            try:
                checkbox = page.ele("css:input[type='checkbox']", timeout=2)
                if checkbox:
                    checkbox.click()
                    log("🔘 已点击 Turnstile checkbox")
            except Exception:
                pass

            time.sleep(3)
        except Exception:
            time.sleep(2)

    return False

def create_browser_options():
    """创建浏览器配置"""
    co = ChromiumOptions()

    # 查找浏览器路径
    browser_path = find_browser_path()
    if browser_path:
        log(f"🌐 浏览器路径: {browser_path}")
        co.set_browser_path(browser_path)
    else:
        log("⚠️ 未找到 Chrome 浏览器，使用默认路径")

    # 反检测参数
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-gpu')
    co.set_argument('--no-first-run')
    co.set_argument('--disable-infobars')
    co.set_argument('--disable-popup-blocking')
    co.set_argument('--disable-extensions')
    co.set_argument('--disable-background-networking')
    co.set_argument('--window-size=1920,1080')

    # 远程调试端口
    port = find_free_port()
    co.set_argument(f'--remote-debugging-port={port}')
    co.set_local_port(port)

    return co

def is_on_x666(url):
    """判断 URL 是否真正在 up.x666.me 上（排除 query 参数中的误匹配）"""
    return url.startswith("https://up.x666.me") or url.startswith("http://up.x666.me")


def screenshot_and_notify(page, filename, caption):
    """截图并发送到 Telegram"""
    try:
        page.get_screenshot(path=filename)
        log(f"📸 已保存截图: {filename}")
        send_telegram_photo(filename, caption)
    except Exception:
        pass


def login_linuxdo(page):
    """在 Linux.do 登录页面输入账号密码并提交"""
    log("⏳ 等待 Cloudflare 验证...")
    if not wait_for_cf(page, timeout=120):
        log("❌ Cloudflare 验证超时")
        screenshot_and_notify(page, "cloudflare_blocked.png",
                              f"Cloudflare 验证未通过\nURL: {page.url}")
        return False
    log("✅ Cloudflare 验证通过")

    # 等待登录表单出现
    log("⏳ 等待登录表单加载...")
    username_input = page.ele("css:#login-account-name", timeout=30)
    if not username_input:
        username_input = page.ele("css:input[name='login']", timeout=10)

    if not username_input:
        # 可能 CF 通过后又跳转到了授权页（之前已有 session）
        if "connect.linux.do" in page.url and "authorize" in page.url:
            log("ℹ️ 已有登录 session，跳转到了授权页")
            return True
        log("❌ 登录表单未出现")
        screenshot_and_notify(page, "no_login_form.png",
                              f"登录表单未出现\nURL: {page.url}")
        return False

    log("🔐 检测到 Linux.do 登录页面，输入账号密码...")

    # 输入用户名
    username_input.clear()
    username_input.input(LINUXDO_USERNAME)
    log(f"✅ 已输入用户名: {LINUXDO_USERNAME}")

    # 输入密码
    password_input = page.ele("css:#login-account-password", timeout=10)
    if not password_input:
        password_input = page.ele("css:input[name='password']", timeout=5)

    if password_input:
        password_input.clear()
        password_input.input(LINUXDO_PASSWORD)
        log("✅ 已输入密码")
    else:
        log("❌ 未找到密码输入框")
        return False

    time.sleep(1)

    # 点击登录按钮
    submit_btn = page.ele("css:#login-button", timeout=10)
    if submit_btn:
        submit_btn.click()
        log("🔘 已点击 Linux.do 登录按钮")
    else:
        log("❌ 未找到登录提交按钮")
        return False

    # 登录后等待并处理可能出现的 Cloudflare Turnstile
    time.sleep(3)
    wait_for_cf(page, timeout=30)

    # 等待 URL 离开 /login（可能跳转到 linux.do 首页、OAuth 授权页、或 up.x666.me）
    log("⏳ 等待登录完成...")
    start = time.time()
    while time.time() - start < 60:
        url = page.url
        if "/login" not in url:
            log(f"✅ 登录成功，已跳转: {url}")
            return True
        time.sleep(1)

    # 检查是否有登录错误提示
    error_msg = ""
    try:
        error_el = page.ele("css:.alert-error, #modal-alert, .login-error", timeout=2)
        if error_el:
            error_msg = error_el.text
    except Exception:
        pass

    if error_msg:
        log(f"❌ Linux.do 登录失败: {error_msg}")
    else:
        log(f"⚠️ 登录后未跳转，当前URL: {page.url}")

    screenshot_and_notify(page, "login_failed.png",
                          f"Linux.do 登录失败\nURL: {page.url}\n{error_msg}")
    return False


def handle_oauth_authorize(page, timeout=15):
    """处理 connect.linux.do OAuth 授权页面，点击「允许」按钮"""
    log("🔍 检查 OAuth 授权页面...")

    # 等待可能跳转到授权页
    start = time.time()
    while time.time() - start < timeout:
        url = page.url
        if "connect.linux.do" in url and "authorize" in url:
            break
        if is_on_x666(url):
            log("ℹ️ 已自动跳转回 up.x666.me（可能之前已授权）")
            return True
        time.sleep(0.5)
    else:
        log(f"⚠️ 未检测到授权页面，当前URL: {page.url}")
        return False

    log("🔐 检测到 OAuth 授权页面")

    # 点击「允许」按钮
    authorize_btn = None
    for text in ["允许", "授权", "Authorize", "Allow"]:
        authorize_btn = page.ele(f"text:{text}", timeout=3)
        if authorize_btn:
            break

    if authorize_btn:
        authorize_btn.click()
        log("✅ 已点击允许按钮")
        time.sleep(2)
        return True
    else:
        log("❌ 未找到授权/允许按钮")
        screenshot_and_notify(page, "no_authorize_btn.png",
                              f"未找到授权按钮\nURL: {page.url}")
        return False


def extract_token_from_network(page, timeout=15):
    """从监听的网络请求中提取 Bearer Token"""
    log("⏳ 等待 status 请求以提取 token...")
    try:
        packet = page.listen.wait(timeout=timeout)
        if packet:
            # 从请求头中提取 Authorization
            auth_header = ""
            if hasattr(packet, 'request') and packet.request:
                headers = packet.request.headers
                if isinstance(headers, dict):
                    auth_header = headers.get('Authorization', '') or headers.get('authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                log(f"✅ 从网络请求提取到 token: {token[:20]}...")
                return token
            else:
                log(f"⚠️ status 请求中无 Bearer token，Authorization: {auth_header[:50] if auth_header else '(空)'}")
    except Exception as e:
        log(f"⚠️ 网络监听提取失败: {e}")
    return None


def extract_token_from_storage(page):
    """从 localStorage / sessionStorage / cookie 中提取 token"""
    # 尝试多种常见的存储 key
    js_code = """
    // 尝试 localStorage
    var keys = ['userToken', 'token', 'bearer_token', 'access_token', 'auth_token', 'jwt'];
    for (var i = 0; i < keys.length; i++) {
        var v = localStorage.getItem(keys[i]);
        if (v && v.length > 20) return v;
    }
    // 尝试 sessionStorage
    for (var i = 0; i < keys.length; i++) {
        var v = sessionStorage.getItem(keys[i]);
        if (v && v.length > 20) return v;
    }
    // 遍历 localStorage 寻找 JWT 格式的值
    for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        var v = localStorage.getItem(k);
        if (v && v.startsWith('eyJ') && v.length > 50) return v;
    }
    // 遍历 sessionStorage
    for (var i = 0; i < sessionStorage.length; i++) {
        var k = sessionStorage.key(i);
        var v = sessionStorage.getItem(k);
        if (v && v.startsWith('eyJ') && v.length > 50) return v;
    }
    return null;
    """
    token = page.run_js(js_code)
    if token:
        log(f"✅ 从浏览器存储提取到 token: {token[:20]}...")
    return token


def get_new_token():
    """通过 DrissionPage 自动化获取新 token"""
    log("🚀 启动浏览器自动化...")

    page = None
    # 最多重试 2 次
    for attempt in range(2):
        try:
            co = create_browser_options()
            page = ChromiumPage(co)
            log(f"✅ 浏览器启动成功 (尝试 {attempt + 1})")
            break
        except Exception as e:
            log(f"⚠️ 浏览器启动失败 (尝试 {attempt + 1}): {e}")
            if attempt == 1:
                log("❌ 浏览器启动失败，放弃")
                return None
            time.sleep(3)

    try:
        # 开始监听 up.x666.me 的 status 请求（用于提取 token）
        page.listen.start('up.x666.me')

        # ===== 第一步：访问 up.x666.me 并点击登录 =====
        log("📍 访问 up.x666.me...")
        page.get("https://up.x666.me")
        time.sleep(3)

        log("🔘 点击登录按钮...")
        login_btn = page.ele("text:登录", timeout=10)
        if not login_btn:
            login_btn = page.ele("css:button.login-btn", timeout=5)
        if login_btn:
            login_btn.click()
            log("✅ 已点击登录按钮")
        else:
            log("❌ 未找到登录按钮")
            screenshot_and_notify(page, "no_login_btn.png",
                                  f"未找到登录按钮\nURL: {page.url}")
            return None

        # ===== 第二步：等待跳转（linux.do 登录页 或 connect.linux.do 授权页）=====
        log("⏳ 等待页面跳转...")
        start = time.time()
        while time.time() - start < 15:
            url = page.url
            if "linux.do" in url:
                break
            time.sleep(0.5)
        else:
            log(f"❌ 未跳转到 Linux.do，当前URL: {page.url}")
            screenshot_and_notify(page, "no_redirect.png",
                                  f"未跳转到 Linux.do\nURL: {page.url}")
            return None

        current_url = page.url
        log(f"📍 跳转到: {current_url}")

        # ===== 第三步：根据跳转目标分别处理 =====
        if "connect.linux.do" in current_url and "authorize" in current_url:
            # 已有 Linux.do session，直接到了 OAuth 授权页
            log("ℹ️ 已有 Linux.do session，直接进入授权页")
            if not handle_oauth_authorize(page, timeout=15):
                return None
        else:
            # 需要先登录 Linux.do
            if not login_linuxdo(page):
                return None

            time.sleep(2)
            current_url = page.url
            log(f"📍 登录后 URL: {current_url}")

            # 登录后可能：1) 自动跳回 up.x666.me  2) 跳转到 OAuth 授权页  3) 停在 linux.do
            if not is_on_x666(current_url):
                if not handle_oauth_authorize(page, timeout=20):
                    # 如果没有检测到授权页也没跳回 x666.me，尝试手动导航
                    if not is_on_x666(page.url):
                        log("⚠️ 未自动跳转，尝试手动访问 up.x666.me...")
                        page.get("https://up.x666.me")
                        time.sleep(3)

        # ===== 第四步：等待回到 up.x666.me =====
        log("⏳ 等待回到 up.x666.me...")
        start = time.time()
        while time.time() - start < 30:
            if is_on_x666(page.url):
                break
            time.sleep(0.5)
        else:
            log(f"❌ 未回到 up.x666.me，当前URL: {page.url}")
            screenshot_and_notify(page, "callback_timeout.png",
                                  f"回调超时\nURL: {page.url}")
            return None

        log(f"✅ 已回到 up.x666.me: {page.url}")

        # 等待页面加载，触发 status 等 API 请求
        time.sleep(5)

        # ===== 第五步：提取 token =====
        # 方法1: 从监听到的网络请求 Authorization header 提取
        token = extract_token_from_network(page, timeout=10)
        if token:
            return token

        # 方法2: 从浏览器存储中提取
        token = extract_token_from_storage(page)
        if token:
            return token

        # 方法3: 刷新页面再次尝试捕获
        log("⏳ 刷新页面重试...")
        page.listen.start('up.x666.me')
        page.refresh()
        time.sleep(5)

        token = extract_token_from_network(page, timeout=10)
        if token:
            return token

        token = extract_token_from_storage(page)
        if token:
            return token

        log("❌ 未能提取到 token")
        screenshot_and_notify(page, "no_token.png",
                              f"登录成功但未提取到 token\nURL: {page.url}")
        return None

    except Exception as e:
        log(f"❌ 发生错误: {e}")
        try:
            screenshot_and_notify(page, "error_screenshot.png",
                                  f"发生错误: {e}\nURL: {page.url}")
            log(f"📍 错误时URL: {page.url}")
            log(f"📄 页面标题: {page.title}")
        except Exception:
            pass
        return None
    finally:
        try:
            page.quit()
        except Exception:
            pass

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
