# 引入需要的依赖库
import requests as re
from bs4 import BeautifulSoup
import gdown
import time
import datetime
import re as re2
import logging
import urllib.parse
from jsonsearch import JsonSearch
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from urllib.parse import quote

from Models import Vless

def_is_pull_latest_blog = True

header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "referer": "https://www.youtube.com/@SFZY666"
}

pageIndex = 0
pageSize = 40
now = datetime.datetime.now()
current_str = now.strftime('%Y-%m-%dT%H:%M:%S') + '- 23:59'
target_url = f'https://skill-note.blogspot.com/search?updated-max={current_str}&max-results={pageSize}'
outfile = "download.log"
logging.basicConfig(filemode='w',
                    filename=outfile,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO,
                    style='%',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    encoding='utf-8'
                    )

# 配置 ChromeOptions
chrome_options = webdriver.ChromeOptions()
chrome_options.headless = True
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)


def get_latest_blog_page_from_ytb(urls):
    result = []
    browser = webdriver.Chrome(options=chrome_options, service=Service(ChromeDriverManager().install()))
    try:
        for url in urls:
            logging.info(f'开始从{url} 中查找blog链接...')
            youtube_video_list_url = url
            browser.get(youtube_video_list_url)
            # 等待并检测是否存在 CAPTCHA 元素（例如，reCAPTCHA 框架）
            wait = WebDriverWait(browser, 10)
            captcha_element = wait.until(EC.presence_of_element_located((By.ID, 'captcha-form')))
            if captcha_element: logging.warning("CAPTCHA 元素已检测到。")
            element = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'ytd-text-inline-expander')))
            more = browser.find_element(By.ID, 'expand')
            more.click()
            des_content = element.find_element(By.TAG_NAME, "yt-attributed-string").get_attribute('outerHTML')
            beautiful_soup = BeautifulSoup(des_content, 'html.parser')
            if beautiful_soup:
                link = beautiful_soup.find_all("a")[-1]
                if link:
                    hand_url = parse_url(link['href'], 'q')
                    logging.info(f"找到博客链接: {hand_url}")
                    result.append(hand_url)
                    time.sleep(10)
    except Exception as e:
        logging.error(e)
    finally:
        browser.close()
    return result


def get_latest_videos_from_ytb():
    result = []
    youtube_video_list_url = 'https://www.youtube.com/@SFZY666/videos'
    res = re.get(youtube_video_list_url)
    if res.status_code != 200:
        logging.error(f"无法访问 {youtube_video_list_url} 页面，状态码：{res.status_code}")
        return result
    bs_content = BeautifulSoup(res.text, 'html.parser')
    scripts = bs_content.find_all("script")
    for script in scripts:

        pattern = r'var\s+ytInitialData\s*=\s*({.*?});'
        if script.string:
            match = re2.search(pattern, script.string, re2.DOTALL)
            if match:
                logging.info(f'找到最新视频标签')
                value = match.group(1)
                try:
                    json_search = JsonSearch(object=value, mode='s')
                    result = unique_preserve_order(json_search.search_all_value(key="videoId"))
                    logging.info(f"json: {result}")
                except Exception as e:
                    logging.error(e)
    return result


def parse_url(url, key):
    # 解析 URL
    parsed_url = urllib.parse.urlparse(url)
    # 提取查询参数
    query_params = urllib.parse.parse_qs(parsed_url.query)
    # 获取 'q' 参数的值
    q_value = query_params.get(key, [None])[0]
    return q_value


def unique_preserve_order(arr):
    prefix = 'https://www.youtube.com/watch?v='
    seen = set()
    unique_arr = []
    for item in arr:
        if item not in seen:
            unique_arr.append(prefix + item)
            seen.add(item)
    return unique_arr


def get_blog_pages(url):
    # 设置访问头
    logging.info(f"正在抓取 {url} 页面...")

    response = re.get(url, headers=header)
    if response.status_code != 200:
        logging.error(f"无法访问 {url} 页面，状态码：{response.status_code}")
        return []

    # 使用 BeautifulSoup 解析 HTML 内容
    results = []
    soup = BeautifulSoup(response.text, 'html.parser')
    blogs_container = soup.find('div', id='content-wrapper')
    if blogs_container is not None:
        blogs = blogs_container.find('div', id='main')
        if blogs is not None:
            links = blogs.find_all('a', class_='post-snippet-link')
            logs = ''
            for link in links:
                title = str.strip(link.text).replace('\n', '')
                results.append(str.strip(link['href']))
                logging.info(f'BlogUrl: {link["href"]} \n Blog标题: {title}, \n')
    return results


def download_from_blog(url):
    logging.info(f"开始查找 {url} 中vpn文件...")
    header['referer'] = target_url
    response = re.get(url, headers=header)
    if response.status_code != 200:
        logging.error(f"无法访问 {url} 页面，状态码：{response.status_code}")
        return []
    page = BeautifulSoup(response.text, 'html.parser')
    headline2_tags = page.find_all("ul", class_='headline2')
    for ul in headline2_tags:
        link_tags = ul.find_all("a")
        for index, item in enumerate(link_tags):
            link = item["href"]
            title = re2.sub(r'[<>:"/\\|?*]', '_', item.text)
            output = quote(url.strip(), safe='=&') + '_A_' + title + "_A_"
            # 替换非法字符
            if link != "" and link.startswith("http"):
                if "点击自动下载" in title:
                    file_name = output + parse_url(link, 'id') + ".txt"
                    logging.info(f"直链下载的地址：{link}")
                    with open(file_name, "wb") as file:
                        for chunk in re.get(link, stream=True).iter_content(chunk_size=8192):
                            if chunk:  # 过滤掉保持活动的新行
                                file.write(chunk)
                elif "drive.google.com" in link:
                    match = re2.search(r'/d/([^/]+)/view', link)
                    if match:
                        file_id = match.group(1)
                        if file_id:
                            output += file_id
                            logging.info(f"匹配到文件ID: {file_id}")
                            download_url = f'https://drive.google.com/uc?id={file_id}'
                            output += '.yaml' if "Clash-" in title else '.txt'
                            # 下载文件
                            try:
                                logging.info(f"Downloading: {download_url} ....  {output}")
                                gdown.download(download_url, output, quiet=False)
                                logging.info(f"Downloaded: {download_url} ....  {output}")
                            except Exception as e:
                                logging.error(f'当前url: {url} 文件名 {output} \n 报错内容：{e}')
                            logging.info(f"{url} 中vpn文件下载成功！")
                        else:
                            logging.error(f"未找到fileId link:{link}")
                    else:
                        logging.warning(f"{link} 中 未匹配到文件id")


def from_blog(is_pull_latest_blog):
    # 第一种方法从博客主页中拉取所有文章链接，目前一共36篇blog，且是随机挂载在一篇博文中，暂时未找到规律，只能穷举再验证链接是否有效
    result = get_blog_pages(target_url)
    if is_pull_latest_blog and len(result) > 0:
        download_from_blog(result[0])
    elif not is_pull_latest_blog and len(result) > 0:
        for url in result:
            download_from_blog(url)
    else:
        logging.warning("未找到blog列表")
    logging.info("脚本执行完毕！！！")


def from_youtube():
    res_videos = get_latest_videos_from_ytb()
    urls = get_latest_blog_page_from_ytb(res_videos)
    if is_pull_latest_blog and len(urls) > 0:
        download_from_blog(urls[0])
    else:
        # 注意多次调用会有验证码需手动点
        for url in urls:
            download_from_blog(url)


# @Todo
def upload_to_alist():
    url = 'http://127.0.0.1:5244/api/fs/form'
    headers = {'Authorization': 'your_token_here', 'Content-Type': 'multipart/form-data',
               'Content-Length': 'size_of_your_file'}
    files = {'file': ('file.jpg', open('C:\\path\\to\\your\\file.jpg', 'rb'))}
    response = re.put(url, headers=headers, files=files)
    print(response.text)


def file_to_database():
    files = os.listdir(os.getcwd())
    txts = [f for f in files if f.endswith('.txt') or f.endswith('.yaml')]
    for txt in txts:
        generate_data_from_file(txt)


def generate_data_from_file(file_name):
    with open(file_name, 'r', encoding='utf-8-sig') as f:
        if "V2ray" in file_name and ".txt" in file_name:
            lines = f.readlines()
            for line in lines:
                content = line.strip().replace("\n", '')
                vless = Vless()
                vless.create_by_vless(vpn_link=content, file_name=file_name, file_type=4, content=content)
        elif "IOS" in file_name and ".txt" in file_name:
            link = f'https://drive.google.com/uc?export=download&id={file_name.split("_A_")[-1].replace(".txt", "")}'
            content = []
            while True:
                line = f.read(1024 * 8)
                content.append(line)
                if not line:
                    break
            vless = Vless()
            vless.create_by_vless(vpn_link=link, file_name=file_name, file_type=3, content=''.join(content))
            # print("IOS:  " + ''.join(content))
        elif "Clash-" in file_name and ".yaml" in file_name:
            print("filename:  " + file_name)
            content = []
            while True:
                line = f.read(1024 * 8)
                content.append(line)
                if not line:
                    break
            vless = Vless()
            vless.create_by_vless(
                vpn_link=f'http://pan.funcc.site/vpn/des/{file_name.split("_A_")[-1].replace(".txt", "")}',
                file_name=file_name,
                file_type=1 if "Clash-meta" in file_name else 2, content=''.join(content))
            # print("Clash-:  " + ''.join(content))


if __name__ == "__main__":
    # from_youtube()
    # from_blog(def_is_pull_latest_blog & False)
    file_to_database()
