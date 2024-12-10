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

is_pull_latest_page = True
header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "referer": "https://www.youtube.com/@SFZY666"
}

pageIndex = 0
pageSize = 10
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


def get_latest_blog_page_from_ytb(urls):
    result = []
    browser = webdriver.Chrome()
    try:
        for url in urls:
            logging.info(f'开始从{url} 中查找blog链接...')
            youtube_video_list_url = url
            browser.get(youtube_video_list_url)
            element = browser.find_element(By.TAG_NAME, 'ytd-text-inline-expander')
            more = browser.find_element(By.ID, 'expand')
            more.click()
            des_content = element.find_element(By.TAG_NAME, "yt-attributed-string").get_attribute('outerHTML')
            beautiful_soup = BeautifulSoup(des_content, 'html.parser')
            if beautiful_soup:
                link = beautiful_soup.find_all("a")[-1]
                if link:
                    hand_url = parse_url(link['href'])
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


def parse_url(url):
    # 解析 URL
    parsed_url = urllib.parse.urlparse(url)
    # 提取查询参数
    query_params = urllib.parse.parse_qs(parsed_url.query)
    # 获取 'q' 参数的值
    q_value = query_params.get('q', [None])[0]
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
            output = url + item.text + "_"
            # 替换非法字符
            output = str.strip(re2.sub(r'[<>:"/\\|?*]', '_', output))
            if link != "" and link.startswith("http"):
                if "点击自动下载" in item.text:
                    file_name = output + str(time.time()) + ".txt"
                    logging.info(f"直链下载的地址：{link}")
                    with open(file_name, "wb") as file:
                        for chunk in re.get(link, stream=True).iter_content(chunk_size=8192):
                            if chunk:  # 过滤掉保持活动的新行
                                file.write(chunk)
                elif "drive.google.com" in link:
                    match = re2.search(r'/d/([^/]+)/view', link)
                    if match:
                        file_id = match.group(1)
                        output += file_id
                        logging.info(f"文件ID: {file_id}")
                        download_url = f'https://drive.google.com/uc?id={file_id}'
                        output += '.yaml' if "Clash-" in item.text else '.txt'
                        # 下载文件
                        logging.info(f"Downloading: {download_url} ....  {output}")
                        try:
                            gdown.download(download_url, output, quiet=False)
                        except Exception as e:
                            logging.error(f'当前url: {url} 文件名 {output} \n 报错内容：{e}')
                        logging.info(f"{url} 中vpn文件下载成功！")
                    else:
                        logging.warning(f"{link} 中 未匹配到文件id")


def from_blog():
    # 第一种方法从博客主页中拉取所有文章链接
    result = get_blog_pages(target_url)
    if is_pull_latest_page:
        download_from_blog(result[0])
    else:
        for url in result:
            download_from_blog(url)
    logging.info("脚本执行完毕！！！")


def from_youtube():
    res_videos = get_latest_videos_from_ytb()
    urls = get_latest_blog_page_from_ytb(res_videos)
    if is_pull_latest_page:
        download_from_blog(urls[0])
    else:
        # 注意抓取多个会被Youtube限流
        for url in urls:
            download_from_blog(url)


if __name__ == "__main__":
    # from_youtube()
    from_blog()
