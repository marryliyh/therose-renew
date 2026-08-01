#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, sys, time, requests
from seleniumbase import SB

# 环境变量
EMAIL = os.environ.get("EMAIL") or ""            # 邮箱   
PASSWORD = os.environ.get("PASSWORD") or ""      # 密码
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN") or ""  # tg通知 bot token
TG_CHAT_ID = os.environ.get("TG_CHAT_ID") or ""      # tg通知 chat_id id

# 目标服务器面板地址
SERVER_URL = os.environ.get("SERVER_URL") or "https://panel.therose.cloud/server/1ce3ddfb"
BASE_URL = "https://client.therose.cloud/login"

# logo 图片路径 (做兜底使用)
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")

# --- 代理配置 ---
IS_PROXY = os.environ.get('IS_PROXY', 'false').lower() == 'true'
PROXY_SERVER = os.environ.get('PROXY_SERVER') or "socks5://127.0.0.1:1080"
REQUESTS_PROXIES = {"http": PROXY_SERVER, "https": PROXY_SERVER} if IS_PROXY else None

# 检查必要变量
if not EMAIL or not PASSWORD:
    print("❌ 请设置环境变量 EMAIL 和 PASSWORD")
    sys.exit(1)

# 获取当前出口IP
def get_current_ip(proxy_server=None):
    proxies = {"http": proxy_server, "https": proxy_server} if (proxy_server and IS_PROXY) else None
    try:
        resp = requests.get("https://api.ip.sb/ip", proxies=proxies, timeout=15)
        if resp.status_code == 200:
            return resp.text.strip()
        return "获取失败"
    except Exception as e:
        print(f"❌ 获取出口IP失败: {e}")
        return "获取失败"

# 点击续期按钮
def click_extend_button(sb):
    selectors = [
        'span:contains("Extend")',
        'button:contains(title="Extend")',
    ]
    for sel in selectors:
        try:
            if sb.find_element(sel, timeout=2):
                print(f"✅ 找到按钮，选择器: {sel}")
                sb.uc_click(sel, timeout=5)
                print("✅ 点击成功")
                return True, {}
        except:
            continue
    try:
        btn = sb.find_element('button:contains("Extend")', timeout=2)
        sb.driver.execute_script("arguments[0].click();", btn)
        print("✅ 通过 JavaScript 点击成功")
        return True, {}
    except Exception as e:
        err = str(e)
        not_time = "was not found" in err or "NoSuchElement" in err
        return False, {"error": err, "not_time": not_time}

# 检查续期是否成功
def check_renewal_success(sb):
    success_selectors = [
        '.alert-success',
        '.alert.alert-success',
        'div[role="alert"].alert-success',
        'div.alert-success',
        'span:contains("successfully purchased")',
        'div:contains("successfully purchased")'
    ]
    
    print("⏳ 等待5秒检查续期结果...")
    time.sleep(5)
    
    for selector in success_selectors:
        try:
            element = sb.find_element(selector, timeout=2)
            if element:
                text = element.text
                print(f"✅ 发现成功提示！选择器: {selector}")
                return True, text
        except:
            continue
    
    try:
        page_source = sb.get_page_source()
        if "successfully purchased" in page_source.lower():
            print("✅ 页面源码中发现 'successfully purchased' 关键词")
            return True, "服务器已成功续期"
    except:
        pass
    
    return False, "未检测到续期成功提示"

# 发送tg通知 (增加 image_path 参数)
def send_tg(token, chat_id, message, image_path=None):
    if not token or not chat_id:
        return
    message = f"【TheRose Cloud】\n{message}"

    # 优先使用传入的实时截图，如果没有则使用本地的 LOGO_PATH
    target_image = image_path if (image_path and os.path.exists(image_path)) else (LOGO_PATH if os.path.exists(LOGO_PATH) else None)

    if target_image:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        try:
            with open(target_image, "rb") as f:
                resp = requests.post(
                    url,
                    data={"chat_id": chat_id, "caption": message},
                    files={"photo": f},
                    timeout=15,
                    proxies=REQUESTS_PROXIES,
                )
            if resp.status_code == 200:
                print(f"📨 Telegram 通知已发送（附带图片: {target_image}）")
                return
            else:
                print(f"⚠️ 带图发送失败，回退为纯文字: {resp.text}")
        except Exception as e:
            print(f"⚠️ 带图发送异常，回退为纯文字: {e}")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10, proxies=REQUESTS_PROXIES)
        if resp.status_code == 200:
            print("📨 Telegram 通知已发送（纯文字）")
        else:
            print(f"❌ Telegram 发送失败: {resp.text}")
    except Exception as e:
        print(f"❌ Telegram 发送异常: {e}")

# 登录流程
def login(sb, email, password):
    print("🌐 打开登录页面...")
    sb.open(BASE_URL)
    sb.wait_for_ready_state_complete()
    sb.sleep(1)
    print("📧 填写邮箱...")
    sb.type('#login_form_email', email, timeout=10)
    print("🔑 填写密码...")
    sb.type('#login_form_password', password, timeout=10)
    time.sleep(1) 
    print("🛡 处理 Turnstile...")
    try:
        sb.uc_gui_click_captcha()
        print("✅ Turnstile 验证已处理")
    except Exception as e:
        print(f"⚠️ uc_gui_click_captcha 执行异常: {e}")
        
    print("⏳ 等待验证 token 生效...")
    sb.sleep(2)

    for attempt in range(3):
        print(f"🔑 点击登录按钮...(第 {attempt + 1} 次)")
        try:
            sb.uc_click('button:contains("Sign in")')
        except Exception as e:
            print(f"⚠️ 点击异常: {e}")

        for _ in range(5):
            current_url = sb.get_current_url()
            if "panel" in current_url:
                print("✅ 登录成功，已跳转到 Dashboard")
                return True, current_url
            time.sleep(1)

        try:
            err_selectors = ['.alert-danger', 'div[role="alert"].alert-danger', '.text-danger']
            for sel in err_selectors:
                if sb.is_element_visible(sel):
                    err_text = sb.get_text(sel)
                    print(f"❌ 登录出现错误提示: {err_text}")
                    sb.save_screenshot("login_failed.png")
                    return False, sb.get_current_url()
        except Exception:
            pass
        print("⚠️ 未跳转，可能是点击未生效或 token 还未就绪，准备重试...")

    print(f"❌ 登录失败，当前 URL: {sb.get_current_url()}")
    sb.save_screenshot("login_failed.png")
    return False, sb.get_current_url()

# ====== 辅助函数：尝试点击按钮 ======
def _try_click_button(sb, selectors, label="按钮"):
    """遍历选择器列表，找到第一个可见可点击的按钮并点击，返回 (True, 使用的选择器) 或 (False, None)"""
    for sel in selectors:
        try:
            if sb.is_element_present(sel):
                if sb.is_element_visible(sel) and sb.is_element_enabled(sel):
                    print(f"✅ 找到【{label}】按钮: {sel}")
                    sb.uc_click(sel, timeout=5)
                    return True, sel
                else:
                    # 存在但不可见/不可点击，尝试 JS 强制点击
                    try:
                        el = sb.driver.find_element("css selector", sel)
                        if el.is_enabled():
                            print(f"✅ 找到【{label}】按钮(JS强制点击): {sel}")
                            sb.driver.execute_script("arguments[0].click();", el)
                            time.sleep(1)
                            return True, sel
                    except Exception:
                        pass
        except Exception:
            continue
    return False, None

# ====== JS 深度扫描按钮 ======
_JS_DEEP_SCAN = """
function getAllText(el) {
    return (el.innerText || el.textContent || '').trim().toLowerCase();
}

// 收集所有可交互元素
const candidates = document.querySelectorAll('button, a[role="button"], [onclick], .btn, input[type="submit"], input[type="button"], [role="tab"], [data-action]');
let found = null;

function isClickable(el) {
    if (!el || el.disabled || el.classList.contains('disabled') || el.getAttribute('aria-disabled') === 'true') return false;
    if (el.offsetParent === null && el.tagName !== 'INPUT') return false;
    return true;
}

// 先找启动类
for (let el of candidates) {
    if (!isClickable(el)) continue;
    const t = getAllText(el);
    const html = (el.innerHTML || '').toLowerCase();
    const action = (el.getAttribute('data-action') || '').toLowerCase();
    const aria = (el.getAttribute('aria-label') || '').toLowerCase();
    const cls = (el.className || '').toLowerCase();
    const val = (el.getAttribute('value') || '').toLowerCase();
    const name = (el.getAttribute('name') || '').toLowerCase();

    if (action === 'start' || action === 'poweron' || action === 'power_on' || action === 'resume' ||
        name === 'start' || name === 'power' || name === 'poweron' ||
        val === 'start' || val === 'power' ||
        t.includes('start') || t.includes('启动') || t.includes('开机') || t.includes('power on') || t.includes('poweron') || t.includes('turn on') || t.includes('resume') ||
        aria.includes('start') || aria.includes('power') || aria.includes('启动') || aria.includes('开机') ||
        html.includes('fa-play') || html.includes('fa-power-off') || html.includes('power-off') ||
        cls.includes('start') || cls.includes('power')) {
        el.click();
        return '启动(JS深度扫描)';
    }
}

// 再找重启类
for (let el of candidates) {
    if (!isClickable(el)) continue;
    const t = getAllText(el);
    const html = (el.innerHTML || '').toLowerCase();
    const action = (el.getAttribute('data-action') || '').toLowerCase();
    const aria = (el.getAttribute('aria-label') || '').toLowerCase();
    const cls = (el.className || '').toLowerCase();
    const val = (el.getAttribute('value') || '').toLowerCase();
    const name = (el.getAttribute('name') || '').toLowerCase();

    if (action === 'restart' || action === 'reboot' || action === 'reload' || action === 'reinstall' ||
        name === 'restart' || name === 'reboot' || name === 'reload' ||
        val === 'restart' || val === 'reboot' || val === 'reload' ||
        t.includes('restart') || t.includes('reboot') || t.includes('reload') || t.includes('重启') || t.includes('重啟') || t.includes('重新启动') || t.includes('重开') || t.includes('重载') ||
        aria.includes('restart') || aria.includes('reboot') || aria.includes('重启') || aria.includes('重新启动') || aria.includes('重啟') ||
        html.includes('fa-redo') || html.includes('fa-sync') || html.includes('fa-rotate') || html.includes('fa-repeat') || html.includes('fa-sync-alt') ||
        cls.includes('restart') || cls.includes('reboot')) {
        el.click();
        return '重启(JS深度扫描)';
    }
}

// 实在找不到，尝试所有按钮中第一个不禁用的
for (let el of candidates) {
    if (isClickable(el)) {
        const t = getAllText(el);
        if (t.length > 0) {
            el.click();
            return '盲猜:' + t.substring(0, 20);
        }
    }
}

// 最后手段：找任何可见的 button 元素点击
const allBtns = document.querySelectorAll('button');
for (let btn of allBtns) {
    if (isClickable(btn)) {
        btn.click();
        return '盲猜button:' + (btn.innerText || '').trim().substring(0, 20);
    }
}

return null;
"""

# 执行启动或重启服务器操作
def start_or_reboot_server(sb, url):
    print(f"🔄 准备进入服务器面板进行启动/重启: {url}")

    try:
        sb.save_screenshot("before_server_action.png")
    except Exception:
        pass

    try:
        sb.open(url)
        sb.wait_for_ready_state_complete()
        print("⏳ 等待页面渲染完成...")
        time.sleep(8)  # 给足时间加载

        # ---------- 1. 独立登录检测 ----------
        try:
            pw_inputs = sb.find_elements('input[type="password"]', timeout=3)
            if pw_inputs and len(pw_inputs) > 0:
                print("🔒 检测到控制面板需要独立登录，正在尝试自动输入账号密码...")
                try:
                    email_inputs = sb.find_elements('input[name="user"], input[type="text"], input[name="email"]', timeout=3)
                    if email_inputs and len(email_inputs) > 0:
                        sb.type('input[name="user"], input[type="text"], input[name="email"]', EMAIL, timeout=5)
                    sb.type('input[type="password"]', PASSWORD, timeout=5)
                    time.sleep(1)

                    try:
                        sb.uc_gui_click_captcha()
                    except Exception:
                        pass

                    time.sleep(3)
                    try:
                        # 优先用 uc_click 绕过检测
                        sb.uc_click('button:contains("Login"), button:contains("Sign in"), button[type="submit"]', timeout=5)
                    except Exception:
                        sb.click('button[type="submit"]')
                    time.sleep(8)
                    print("✅ 控制面板独立登录完成")
                except Exception as e:
                    print(f"⚠️ 自动登录控制面板发生错误: {e}")
        except Exception:
            pass

        # ---------- 2. 检查是否在详情页 ----------
        current_url = sb.get_current_url()
        print(f"📍 当前页面 URL: {current_url}")
        if "/server/" not in current_url and "/node/" not in current_url:
            print("🔀 检测到不在服务器详情页，正在强制进入目标服务器控制台...")
            sb.open(url)
            sb.wait_for_ready_state_complete()
            time.sleep(6)
            current_url = sb.get_current_url()
            print(f"📍 导航后 URL: {current_url}")

        try:
            sb.save_screenshot("before_click.png")
        except Exception:
            pass

        # ---------- 3. 多轮重试查找按钮 ----------
        btn_clicked = False
        action_name = ""

        for retry in range(3):
            print(f"🔍 第 {retry + 1} 轮查找按钮...")

            # --- 先找启动按钮（服务器离线状态）---
            if not btn_clicked:
                start_selectors = [
                    # 中文
                    'button:contains("启动")',
                    'button:contains("开机")',
                    'button:contains("开启")',
                    # 英文
                    'button:contains("Start")',
                    'button:contains("Power On")',
                    'button:contains("PowerOn")',
                    'button:contains("Turn On")',
                    'button:contains("Resume")',
                    # data 属性
                    'button[data-action="start"]',
                    'button[value="start"]',
                    'button[name="start"]',
                    # 图标
                    'button i.fa-play',
                    'button i.fa-power-off',
                    'button svg[data-icon="play"]',
                    'button svg[data-icon="power-off"]',
                    # aria
                    'button[aria-label*="start" i]',
                    'button[aria-label*="power" i]',
                    'button[aria-label*="启动" i]',
                    'button[aria-label*="开机" i]',
                    # 链接/span 包裹的按钮
                    'a:contains("启动"), a:contains("Start"), a:contains("Power On")',
                    'span:contains("启动") button, span:contains("Start") button',
                ]
                ok, used_sel = _try_click_button(sb, start_selectors, "启动")
                if ok:
                    btn_clicked = True
                    action_name = "启动"

            # --- 再找重启按钮（服务器运行状态）---
            if not btn_clicked:
                reboot_selectors = [
                    # 中文
                    'button:contains("重启")',
                    'button:contains("重啟")',
                    'button:contains("重新启动")',
                    'button:contains("重开")',
                    'button:contains("重载")',
                    # 英文
                    'button:contains("Restart")',
                    'button:contains("Reboot")',
                    'button:contains("Reload")',
                    'button:contains("Reconnect")',
                    # data 属性
                    'button[data-action="restart"]',
                    'button[data-action="reboot"]',
                    'button[data-action="reload"]',
                    'button[value="restart"]',
                    'button[name="restart"]',
                    # 图标
                    'button i.fa-redo',
                    'button i.fa-sync',
                    'button i.fa-sync-alt',
                    'button i.fa-rotate',
                    'button i.fa-repeat',
                    'button svg[data-icon="redo"]',
                    'button svg[data-icon="sync"]',
                    'button svg[data-icon="rotate"]',
                    'button svg[data-icon="repeat"]',
                    # aria
                    'button[aria-label*="restart" i]',
                    'button[aria-label*="reboot" i]',
                    'button[aria-label*="重启" i]',
                    'button[aria-label*="重新启动" i]',
                    'button[aria-label*="重啟" i]',
                    # 链接/span 包裹的按钮
                    'a:contains("重启"), a:contains("Restart"), a:contains("Reboot")',
                    'span:contains("重启") button, span:contains("Restart") button',
                ]
                ok, used_sel = _try_click_button(sb, reboot_selectors, "重启")
                if ok:
                    btn_clicked = True
                    action_name = "重启"

            if btn_clicked:
                break

            if retry < 2:
                print(f"⏳ 本轮未找到按钮，刷新页面重试（第{retry + 1}次）...")
                sb.driver.refresh()
                sb.wait_for_ready_state_complete()
                time.sleep(6)
                # 刷新后重新检查独立登录
                try:
                    pw_inputs = sb.find_elements('input[type="password"]', timeout=2)
                    if pw_inputs and len(pw_inputs) > 0:
                        print("🔒 刷新后检测到登录框，重新登录...")
                        sb.type('input[type="password"]', PASSWORD, timeout=3)
                        time.sleep(1)
                        try:
                            sb.uc_click('button:contains("Login"), button:contains("Sign in"), button[type="submit"]', timeout=5)
                        except Exception:
                            pass
                        time.sleep(8)
                except Exception:
                    pass

        # ---------- 4. JS 深度扫描 ----------
        if not btn_clicked:
            print("⚠️ 常规选择器均未找到按钮，使用 JavaScript 深度扫描...")
            try:
                js_result = sb.driver.execute_script(_JS_DEEP_SCAN)
                if js_result:
                    btn_clicked = True
                    action_name = js_result
                    print(f"✅ 通过 JavaScript 深度扫描成功点击了【{action_name}】按钮")
                else:
                    print("⚠️ JavaScript 深度扫描也未找到任何可用按钮")
            except Exception as ex:
                print(f"⚠️ JS 深度扫描执行失败: {ex}")

        # ---------- 5. 最终手段：刷新 + JS 重试 ----------
        if not btn_clicked:
            print("🔄 最终手段：刷新页面并再次尝试...")
            try:
                sb.open(url)
                sb.wait_for_ready_state_complete()
                time.sleep(10)
                sb.save_screenshot("final_retry.png")

                js_result = sb.driver.execute_script(_JS_DEEP_SCAN)
                if js_result:
                    btn_clicked = True
                    action_name = js_result + "(最终重试)"
                    print(f"✅ 最终手段点击成功: {action_name}")
                else:
                    print("❌ 最终手段仍未找到任何按钮")
            except Exception as ex:
                print(f"⚠️ 最终手段异常: {ex}")

        if btn_clicked:
            print(f"⏳ 等待 {action_name} 命令发送...")
            time.sleep(3)
            try:
                sb.save_screenshot("after_action.png")
            except Exception:
                pass
            return True, f"已成功发送 [{action_name}] 指令"
        else:
            try:
                sb.save_screenshot("button_not_found.png")
                print("📸 已保存页面截图到 button_not_found.png，请查看页面实际状态")
            except Exception:
                pass
            return False, "页面上未检测到可用的启动或重启按钮（已截图保存）"

    except Exception as e:
        return False, f"维护操作发生异常: {e}"

# 主流程
def main():
    print("🚀 启动浏览器")

    if IS_PROXY:
        print(f"⚙️ 代理已启用: {PROXY_SERVER}")
    else:
        print("🌐 直连模式（未使用代理）")

    current_ip = get_current_ip(PROXY_SERVER)
    print(f"🎯 当前出口IP: {current_ip}")

    sb_kwargs = {"uc": True, "headless": False}
    if IS_PROXY:
        sb_kwargs["proxy"] = PROXY_SERVER

    with SB(**sb_kwargs) as sb:
        success, url = login(sb, EMAIL, PASSWORD)
        
        if not success:
            msg = f"❌ 登录失败，请检查账号密码或验证码拦截情况。"
            print(msg)
            # 发送失败并附带截图
            send_tg(TG_BOT_TOKEN, TG_CHAT_ID, msg, image_path="login_failed.png")
            return

        print("📄 开始续期流程...")
        ok, info = click_extend_button(sb)
        
        if not ok:
            if info.get("not_time"):
                msg_renewal = "⏳ 未到续期时间，Extend 按钮尚未出现（一般到期前半小时开放），本次跳过。"
            else:
                msg_renewal = f"❌ 续期失败，未找到 Extend 按钮 ({info.get('error')})。"
            print(msg_renewal)
        else:
            time.sleep(1)
            try:
                button = sb.find_element('button:contains("Order now")', timeout=5)
                if button:
                    print("🛒 点击 Order now 按钮...")
                    sb.uc_click('button:contains("Order now")')
                else:
                    msg_renewal = "❌ 续期异常，未找到 Order now 按钮。"
                    print(msg_renewal)
            except Exception as e:
                msg_renewal = f"❌ 点击 Order now 发生错误: {e}。"
                print(msg_renewal)
            
            print("🔍 检查续期结果...")
            renewal_success, renewal_msg = check_renewal_success(sb)
            if renewal_success:
                msg_renewal = f"✅ 续期成功！{renewal_msg}"
                sb.save_screenshot("renewal_success.png")
            else:
                msg_renewal = f"❌ 续期可能失败: {renewal_msg}"
                sb.save_screenshot("renewal_failed.png")
            print(msg_renewal)

        print("🔄 开始检查并执行服务器启动/重启维护...")
        reboot_ok, reboot_msg = start_or_reboot_server(sb, SERVER_URL)
        
        if reboot_ok:
            msg_reboot = f"✅ 自动状态维护成功: {reboot_msg}"
        else:
            msg_reboot = f"⚠️ 状态维护失败: {reboot_msg}"
        print(msg_reboot)
        
        # 截图保存最终状态，并推送到 Telegram
        final_image = "final_result.png"
        sb.save_screenshot(final_image)
        
        final_msg = f"IP: {current_ip}\n\n{msg_renewal}\n---\n{msg_reboot}"
        send_tg(TG_BOT_TOKEN, TG_CHAT_ID, final_msg, image_path=final_image)

    print("🏁 脚本执行完毕")

if __name__ == "__main__":
    main()
