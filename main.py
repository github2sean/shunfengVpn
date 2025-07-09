# 引入需要的依赖库
import time
import requests as req
from bs4 import BeautifulSoup
import gdown
import datetime
import re as rex
import logging
import urllib.parse
from jsonsearch import JsonSearch
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
logger = logging.getLogger(__name__)
pattern = r'"description"\s*:\s*{\s*"simpleText"\s*:\s*"[^"]*本期免费节点获取地址：\s*(https?://[^\s"]+?\.html)'


def time_wrapper(func):
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        logger.info(f"{func.__name__} 总耗时：{end_time - start_time}")
        return result

    return wrapper


@time_wrapper
def get_latest_blog_url_from_ytb(urls):
    result = []
    try:
        if urls and len(urls) > 0:
            logger.info(f'开始从{urls[0]} 中查找blog链接...')
            youtube_video_list_url = urls[0]
            res = req.get(youtube_video_list_url)
            if res and res.status_code == 200:
                text = res.text
                # print("text", text)
                matches = rex.search(pattern, text, rex.DOTALL)
                if matches:
                    result.append(matches.group(1))
            else:
                logger.warning("页面无返回！！！")
    except Exception as e:
        logger.error(e)
    finally:
        return result


def get_latest_videos_from_ytb():
    result = []
    youtube_video_list_url = 'https://www.youtube.com/@SFZY666/videos'
    res = req.get(youtube_video_list_url)
    if res.status_code != 200:
        logger.error(f"无法访问 {youtube_video_list_url} 页面，状态码：{res.status_code}")
        return result
    bs_content = BeautifulSoup(res.text, 'html.parser')
    scripts = bs_content.find_all("script")
    for script in scripts:

        pattern = r'var\s+ytInitialData\s*=\s*({.*?});'
        if script.string:
            match = rex.search(pattern, script.string, rex.DOTALL)
            if match:
                logger.info(f'找到最新视频标签')
                value = match.group(1)
                try:
                    json_search = JsonSearch(object=value, mode='s')
                    result = unique_preserve_order(json_search.search_all_value(key="videoId"))
                    logger.info(f"json: {result}")
                except Exception as e:
                    logger.error(e)
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
    logger.info(f"正在抓取 {url} 页面...")

    response = req.get(url, headers=header)
    if response.status_code != 200:
        logger.error(f"无法访问 {url} 页面，状态码：{response.status_code}")
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
                logger.info(f'BlogUrl: {link["href"]} \n Blog标题: {title}, \n')
    return results


@time_wrapper
def download_from_blog(url):
    logger.info(f"开始查找 {url} 中vpn文件...")
    header['referer'] = target_url
    response = req.get(url, headers=header)
    if response.status_code != 200:
        logger.error(f"无法访问 {url} 页面，状态码：{response.status_code}")
        return []
    page = BeautifulSoup(response.text, 'html.parser')
    headline2_tags = page.find_all("ul", class_='headline2')
    logger.info("=============开始下载=============")
    for ul in headline2_tags:
        link_tags = ul.find_all("a")
        for index, item in enumerate(link_tags):
            link = item["href"]
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
            title = rex.sub(r'[<>:"/\\|?*]', '_', item.text)
            output = 'assets' + os.sep + quote(url.strip(), safe='=&') + '_A_' + title + "_A_"
            os.makedirs(os.path.dirname(output), exist_ok=True)
            # 替换非法字符
            if link != "" and link.startswith("http"):
                if "点击自动下载" in title:
                    file_name = output + parse_url(link, 'id') + "_A_" + current_time + ".txt"
                    logger.info(f"直链下载的地址：{link}")
                    with open(file_name, "wb") as file:
                        for chunk in req.get(link, stream=True).iter_content(chunk_size=8192):
                            if chunk:  # 过滤掉保持活动的新行
                                file.write(chunk)
                elif "drive.google.com" in link:
                    match = rex.search(r'/d/([^/]+)/view', link)
                    if match:
                        file_id = match.group(1)
                        if file_id:
                            output += file_id
                            logger.info(f"匹配到文件ID: {file_id}")
                            download_url = f'https://drive.google.com/uc?id={file_id}'
                            output += "_A_" + current_time + ('.yaml' if "Clash-" in title else '.txt')
                            # 下载文件
                            try:
                                logger.info(f"Downloading: {download_url} ....  {output}")
                                gdown.download(download_url, output, quiet=False)
                                logger.info(f"Downloaded: {download_url} ....  {output}")
                            except Exception as e:
                                logger.error(f'当前url: {url} 文件名 {output} \n 报错内容：{e}')
                            logger.info(f"{url} 中vpn文件下载成功！")
                        else:
                            logger.error(f"未找到fileId link:{link}")
                    else:
                        logger.warning(f"{link} 中 未匹配到文件id")
    logger.info("=============下载完成=============")


def from_blog(is_pull_latest_blog):
    # 第一种方法从博客主页中拉取所有文章链接，目前一共36篇blog，且是随机挂载在一篇博文中，暂时未找到规律，只能穷举再验证链接是否有效
    result = get_blog_pages(target_url)
    if is_pull_latest_blog and len(result) > 0:
        download_from_blog(result[0])
    elif not is_pull_latest_blog and len(result) > 0:
        for url in result:
            download_from_blog(url)
    else:
        logger.warning("未找到blog列表")
    logger.info("脚本执行完毕！！！")


@time_wrapper
def from_youtube():
    res_videos = get_latest_videos_from_ytb()
    urls = get_latest_blog_url_from_ytb(res_videos)
    if def_is_pull_latest_blog and len(urls) > 0:
        download_from_blog(urls[0])
    else:
        logger.warning("未找到blog地址！")


# @Todo
def upload_to_alist():
    url = 'http://127.0.0.1:5244/api/fs/form'
    headers = {'Authorization': 'your_token_here', 'Content-Type': 'multipart/form-data',
               'Content-Length': 'size_of_your_file'}
    files = {'file': ('file.jpg', open('C:\\path\\to\\your\\file.jpg', 'rb'))}
    response = req.put(url, headers=headers, files=files)
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
    from_youtube()
    # from_blog(def_is_pull_latest_blog & False)
    # file_to_database()
