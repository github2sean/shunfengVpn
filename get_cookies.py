import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# 配置环境变量，禁用 DBus
os.environ['DBUS_SESSION_BUS_ADDRESS'] = '/dev/null'


def youtube_login_headless(
        email: str,
        password: str,
        cookie_file: str = "bnl_cookies.txt",
        two_step_wait: int = 120  # 两步验证预留时间（秒）
):
    """
    Linux 无头模式下登录 YouTube，提取 Cookie 并保存为 yt-dlp 兼容格式
    :param email: YouTube 账号邮箱
    :param password: YouTube 账号密码
    :param cookie_file: Cookie 保存路径
    :param two_step_wait: 两步验证手动输入时间（默认 120 秒）
    """
    # 1. 配置 Linux 无头 Chrome 选项（关键！适配 Linux 环境）
    chrome_options = webdriver.ChromeOptions()
    # 核心无头模式配置
    chrome_options.add_argument("--headless=new")  # 新版无头模式（必须）
    # Linux 权限/依赖适配
    chrome_options.add_argument("--no-sandbox")  # 解决 Linux 非 root 权限问题
    chrome_options.add_argument("--disable-gpu")  # 禁用 GPU（Linux 无头模式必需）
    chrome_options.add_argument("--disable-dev-shm-usage")  # 解决 /dev/shm 空间不足
    chrome_options.add_argument("--remote-debugging-port=9222")  # 可选，调试用
    chrome_options.add_argument("--disable-audio-output")  # 消除音频报错
    chrome_options.add_argument("--disable-desktop-notifications")  # 消除通知报错
    # 绕过 Google 反爬检测
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    # 模拟正常浏览器 UA
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # 2. 启动无头 Chrome（自动匹配 Chrome 版本）
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    # 禁用 selenium 特征（进一步绕过反爬）
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    try:
        # 3. 打开 YouTube 登录页
        driver.get("https://accounts.google.com/ServiceLogin?service=youtube")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "identifierId")))
        print("✅ 加载登录页完成")

        # 4. 输入邮箱
        email_input = driver.find_element(By.ID, "identifierId")
        email_input.send_keys(email)
        email_input.send_keys(Keys.ENTER)
        time.sleep(3)
        print("✅ 输入邮箱完成")

        # 5. 输入密码
        password_input = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "Passwd")))
        password_input.send_keys(password)
        password_input.send_keys(Keys.ENTER)
        time.sleep(5)
        print("✅ 输入密码完成")

        # 6. 处理两步验证（关键！无头模式下需手动验证）
        try:
            # 检测两步验证输入框
            WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.ID, "totpPin")))
            print(f"\n⚠️  检测到两步验证！请在 {two_step_wait} 秒内完成以下操作：")
            print("1. 打开浏览器访问：http://localhost:9222")  # 无头模式调试界面
            print("2. 在弹出的界面中完成两步验证输入")
            time.sleep(two_step_wait)  # 预留时间手动验证
        except:
            print("✅ 无两步验证，继续登录...")
            time.sleep(3)

        # 7. 验证登录成功
        driver.get("https://www.youtube.com/")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "ytd-app")))
        if "Sign in" not in driver.page_source:
            print("✅ YouTube 登录成功！")
        else:
            raise Exception("❌ 登录失败，请检查账号密码或两步验证")

        # 8. 提取 Cookie 并保存为 Netscape 格式（yt-dlp 兼容）
        cookies = driver.get_cookies()
        with open(cookie_file, "w", encoding="utf-8") as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# https://curl.se/docs/http-cookies.html\n\n")
            for cookie in cookies:
                if not cookie.get("domain") or not cookie.get("name"):
                    continue
                # Netscape 格式：domain\tflag\tpath\tsecure\texpiration\tname\tvalue
                domain = cookie["domain"]
                flag = "TRUE" if domain.startswith(".") else "FALSE"
                path = cookie.get("path", "/")
                secure = "TRUE" if cookie.get("secure") else "FALSE"
                expiry = cookie.get("expiry", 0)
                name = cookie["name"]
                value = cookie["value"]
                f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")

        print(f"✅ Cookie 已保存到：{cookie_file}")

    except Exception as e:
        print(f"❌ 执行失败：{str(e)}")
    finally:
        driver.quit()
        print("✅ 浏览器已关闭")


# ------------------- 调用示例 -------------------
if __name__ == "__main__":
    # 替换为你的 YouTube 账号信息
    YOUTUBE_EMAIL = "seanzq0331@gmail.com"
    YOUTUBE_PASSWORD = "S1234z5678q"

    # 执行无头登录
    youtube_login_headless(YOUTUBE_EMAIL, YOUTUBE_PASSWORD)
