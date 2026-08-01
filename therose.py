#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, sys, time, json, requests
from urllib.parse import urljoin
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

# ====== 提取页面可交互元素（Python 解析 HTML，不依赖 JS）======
def _dump_page_source(sb, tag):
    """通过 get_page_source 获取 HTML，提取关键信息用于调试"""
    try:
        html = sb.get_page_source()
        if not html:
            print(f"⚠️ [{tag}] get_page_source 返回空")
            return
        
        from html.parser import HTMLParser
        
        class ButtonFinder(HTMLParser):
            def __init__(self):
                super().__init__()
                self.buttons = []
                self.in_tag = False
                self.current = {}
                self.skip = False
            
            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                tag = tag.lower()
                
                if tag in ('button', 'a', 'input', 'span'):
                    rtype = attrs_dict.get('type', '')
                    rrole = attrs_dict.get('role', '')
                    if tag == 'button' or rtype in ('submit', 'button') or rrole == 'button' or tag == 'a':
                        self.current = {
                            'tag': tag,
                            'type': rtype,
                            'text': '',
                            'title': attrs_dict.get('title', ''),
                            'aria-label': attrs_dict.get('aria-label', ''),
                            'data-action': attrs_dict.get('data-action', ''),
                            'name': attrs_dict.get('name', ''),
                            'value': attrs_dict.get('value', ''),
                            'class': attrs_dict.get('class', ''),
                            'href': attrs_dict.get('href', ''),
                            'id': attrs_dict.get('id', ''),
                        }
                        self.in_tag = True
                        self.skip = False
                elif tag in ('script', 'style'):
                    self.skip = True
            
            def handle_data(self, data):
                if self.in_tag and not self.skip:
                    self.current['text'] += data.strip()
            
            def handle_endtag(self, tag):
                if self.in_tag and tag.lower() in ('button', 'a', 'input', 'span'):
                    text = self.current['text'][:60]
                    if text or self.current['title'] or self.current['aria-label'] or self.current['data-action']:
                        self.buttons.append(self.current)
                    self.in_tag = False
                self.skip = False
        
        finder = ButtonFinder()
        finder.feed(html)
        
        print(f"📋 [{tag}] 页面可交互元素 ({len(finder.buttons)}个):")
        for idx, el in enumerate(finder.buttons):
            parts = []
            if el['text']: parts.append(f"text='{el['text']}'")
            if el['title']: parts.append(f"title='{el['title']}'")
            if el['aria-label']: parts.append(f"aria='{el['aria-label']}'")
            if el['data-action']: parts.append(f"action='{el['data-action']}'")
            if el['name']: parts.append(f"name='{el['name']}'")
            if el['value']: parts.append(f"value='{el['value']}'")
            if el['class']: parts.append(f"class='{el['class']}'")
            if el['href']: parts.append(f"href='{el['href']}'")
            if el['id']: parts.append(f"id='{el['id']}'")
            print(f"   [{idx}] <{el['tag']}> {' '.join(parts)}")
        
        # 也打印页面标题
        title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
        title = title_match.group(1) if title_match else "(无标题)"
        print(f"📋 [{tag}] 页面标题: {title}")
        
        # 检查 iframe
        iframe_count = html.lower().count('<iframe')
        if iframe_count > 0:
            print(f"📋 [{tag}] 页面包含 {iframe_count} 个 iframe")
        
        # 检查页面是否包含关键文字
        text_lower = html.lower()
        for keyword in ['start', '启动', 'restart', '重启', 'reboot', 'power', '开机', 'login', 'sign in', '登录']:
            if keyword in text_lower:
                print(f"📋 [{tag}] 页面包含关键词: '{keyword}'")
        
    except Exception as e:
        print(f"⚠️ [{tag}] 解析页面失败: {e}")

# ====== 启动/重启服务器 ======
def start_or_reboot_server(sb, server_url):
    """
    启动或重启服务器。
    策略：先尝试直达 server_url，如果 404 则从面板首页找服务器列表导航进去。
    """
    print(f"🔄 准备进入服务器面板进行启动/重启")

    def _is_404(sb):
        """检查当前页面是否显示 404 / 资源不存在"""
        try:
            html = (sb.get_page_source() or '').lower()
            if 'something went wrong' in html and 'does not exist' in html:
                return True
            title = (sb.get_title() or '').lower()
            if '404' in title or 'not found' in title:
                return True
        except:
            pass
        return False

    def _is_login_page(sb):
        """判断当前页面是否是登录页"""
        try:
            url = sb.get_current_url().lower()
            if 'login' in url or 'signin' in url or 'auth' in url:
                return True
            pw_inputs = sb.find_elements('input[type="password"]', timeout=2)
            if pw_inputs and len(pw_inputs) > 0:
                return True
            html = (sb.get_page_source() or '').lower()
            if ('sign in' in html or 'login' in html) and 'password' in html:
                return True
        except:
            pass
        return False

    def _try_login_panel(sb):
        """在面板登录页尝试登录"""
        print("🔒 检测到登录页，尝试自动登录...")
        _dump_page_source(sb, "登录页")
        try:
            pw_inputs = sb.find_elements('input[type="password"]', timeout=3)
            if not pw_inputs or len(pw_inputs) == 0:
                print("⚠️ 未找到密码框")
                return False

            # 填邮箱
            email_filled = False
            email_sels = [
                'input[type="text"]', 'input[type="email"]', 'input[name="user"]',
                'input[name="email"]', 'input[name="username"]', 'input[name="login"]'
            ]
            for sel in email_sels:
                try:
                    inputs = sb.find_elements(sel, timeout=2)
                    for inp in inputs:
                        try:
                            if inp.is_displayed():
                                inp.clear()
                                inp.send_keys(EMAIL)
                                email_filled = True
                                break
                        except:
                            continue
                    if email_filled:
                        break
                except:
                    continue
            if not email_filled:
                # 试试第一个可见输入框
                try:
                    all_ins = sb.find_elements('input:not([type="hidden"]):not([type="password"])', timeout=3)
                    for inp in all_ins:
                        if inp.is_displayed():
                            inp.clear()
                            inp.send_keys(EMAIL)
                            email_filled = True
                            break
                except:
                    pass

            # 填密码
            try:
                pw = sb.find_element('input[type="password"]', timeout=3)
                pw.clear()
                pw.send_keys(PASSWORD)
            except Exception as e:
                print(f"⚠️ 填密码失败: {e}")

            time.sleep(1)
            try:
                sb.uc_gui_click_captcha()
            except:
                pass
            time.sleep(3)

            # 点登录
            clicked = False
            for sel in [
                'button:contains("Sign in")', 'button:contains("Login")',
                'button:contains("Log in")', 'button:contains("登录")',
                'button[type="submit"]', 'input[type="submit"]'
            ]:
                try:
                    if sb.is_element_present(sel):
                        sb.uc_click(sel, timeout=5)
                        clicked = True
                        break
                except:
                    continue
            if not clicked:
                try:
                    sb.driver.execute_script(
                        "var b=document.querySelector('button[type=submit],input[type=submit]');"
                        "if(b){b.click()}"
                    )
                    clicked = True
                except:
                    pass

            if clicked:
                time.sleep(10)
                print(f"📍 登录后 URL: {sb.get_current_url()}")
                _dump_page_source(sb, "登录后")
                return True
            return False
        except Exception as e:
            print(f"⚠️ 登录异常: {e}")
            return False

    def _nav_to(sb, target_url, desc="页面"):
        """导航到目标，检测登录并自动处理，返回当前 URL"""
        print(f"🌐 导航到{desc}: {target_url}")
        sb.open(target_url)
        sb.wait_for_ready_state_complete()
        time.sleep(8)
        for _ in range(3):
            if _is_login_page(sb):
                _try_login_panel(sb)
                # 登录后重新导航
                sb.open(target_url)
                sb.wait_for_ready_state_complete()
                time.sleep(10)
            else:
                break
        _dump_page_source(sb, desc)
        return sb.get_current_url()

    def _find_server_from_dashboard(sb):
        """从面板首页提取服务器链接，返回第一个可用的服务器详情页 URL"""
        print("🔍 从面板首页查找服务器链接...")
        html = sb.get_page_source() or ''
        # 提取所有包含 server 的 href
        all_urls = re.findall(r'href="([^"]*server[^"]*)"', html, re.IGNORECASE)
        all_urls = list(set(all_urls))
        print(f"📋 找到 {len(all_urls)} 个服务器链接:")
        for u in all_urls:
            print(f"   🔗 {u}")

        # 优先匹配 SERVER_URL 中的 server_id
        m = re.search(r'/server/([^/]+)', server_url)
        target_id = m.group(1) if m else None
        if target_id:
            for u in all_urls:
                if target_id in u:
                    full = u if u.startswith('http') else urljoin(sb.get_current_url(), u)
                    print(f"✅ 匹配到服务器 ID {target_id}: {full}")
                    return full

        if all_urls:
            first = all_urls[0]
            full = first if first.startswith('http') else urljoin(sb.get_current_url(), first)
            print(f"➡️ 使用第一个服务器链接: {full}")
            return full
        return None

    def _find_and_click_button(sb):
        """在服务器详情页找启动/重启按钮"""
        for retry in range(3):
            print(f"🔍 第 {retry+1} 轮查找按钮...")
            _dump_page_source(sb, f"查找-第{retry+1}轮")

            if _is_404(sb):
                return False, "404"

            # 启动按钮
            start_sels = [
                'button:contains("启动")', 'button:contains("开机")', 'button:contains("开启")',
                'button:contains("Start")', 'button:contains("Power On")', 'button:contains("PowerOn")',
                'button:contains("Turn On")', 'button:contains("Resume")',
                'button[data-action="start"]', 'button[value="start"]', 'button[name="start"]',
                'button i.fa-play', 'button i.fa-power-off',
                'button svg[data-icon="play"]', 'button svg[data-icon="power-off"]',
                'button[aria-label*="start" i]', 'button[aria-label*="power" i]',
                'button[aria-label*="启动" i]', 'button[aria-label*="开机" i]',
                'a:contains("启动"), a:contains("Start"), a:contains("Power On")',
            ]
            ok, _ = _try_click_button(sb, start_sels, "启动")
            if ok:
                return True, "启动"

            # 重启按钮
            reboot_sels = [
                'button:contains("重启")', 'button:contains("重啟")', 'button:contains("重新启动")',
                'button:contains("重开")', 'button:contains("重载")',
                'button:contains("Restart")', 'button:contains("Reboot")', 'button:contains("Reload")',
                'button:contains("Reconnect")',
                'button[data-action="restart"]', 'button[data-action="reboot"]', 'button[data-action="reload"]',
                'button[value="restart"]', 'button[name="restart"]',
                'button i.fa-redo', 'button i.fa-sync', 'button i.fa-sync-alt',
                'button i.fa-rotate', 'button i.fa-repeat',
                'button svg[data-icon="redo"]', 'button svg[data-icon="sync"]',
                'button svg[data-icon="rotate"]', 'button svg[data-icon="repeat"]',
                'button[aria-label*="restart" i]', 'button[aria-label*="reboot" i]',
                'button[aria-label*="重启" i]', 'button[aria-label*="重新启动" i]', 'button[aria-label*="重啟" i]',
                'a:contains("重启"), a:contains("Restart"), a:contains("Reboot")',
            ]
            ok, _ = _try_click_button(sb, reboot_sels, "重启")
            if ok:
                return True, "重启"

            if retry < 2:
                print(f"⏳ 刷新重试...")
                sb.driver.refresh()
                sb.wait_for_ready_state_complete()
                time.sleep(8)

        # JS 深度扫描
        try:
            r = sb.driver.execute_script(_JS_DEEP_SCAN)
            if r:
                return True, str(r)
        except:
            pass

        return False, None

    # ====== 主流程 ======
    try:
        sb.save_screenshot("before_server_action.png")
    except:
        pass

    # 先尝试直达 server_url
    _nav_to(sb, server_url, "服务器详情页")

    if _is_404(sb):
        print("⚠️ 服务器 URL 返回 404，改从面板首页导航...")
        # 去面板首页
        _nav_to(sb, "https://panel.therose.cloud/", "面板首页")
        found = _find_server_from_dashboard(sb)
        if found:
            _nav_to(sb, found, "服务器详情页(从首页)")
        else:
            print("❌ 面板首页未找到服务器链接")
            sb.save_screenshot("no_server_links.png")
            return False, "面板首页未找到服务器链接"

    # 找按钮
    ok, action = _find_and_click_button(sb)

    if ok:
        print(f"⏳ 等待 {action} 完成...")
        time.sleep(3)
        try:
            sb.save_screenshot("after_action.png")
        except:
            pass
        return True, f"已发送 [{action}] 指令"
    else:
        try:
            sb.save_screenshot("button_not_found.png")
        except:
            pass
        if action == "404":
            return False, "服务器页面返回 404，资源不存在"
        return False, "未找到启动/重启按钮（已截图保存）"

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
