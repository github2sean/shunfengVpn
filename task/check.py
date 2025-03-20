import base64
import json
import socket
from Models import Vless
from urllib.parse import urlsplit
from subprocess import Popen, PIPE
from urllib.request import urlopen


def speedtest(link):
    process = Popen(["./vmessspeed", link], stdout=PIPE)
    stdout = process.communicate()[0]

    return stdout


def select_all_vless():
    vless = Vless()
    vless.select().where(Vless.type == 3)


def get_vless_from_des(subscribe_url):
    return_content = ''
    try:
        return_content = urlopen(subscribe_url).read()
    except Exception as e:
        print(e)
    return return_content


def decode_vmess(url):
    if is_base64(url):
        # 去掉前缀
        url = urlsplit(url)
        print(f"url: {url} chardet:  {url.netloc} ")
        base = base64.b64decode(url.netloc).decode('utf-8', errors='ignore')
        print(f"base:  {base}")
        res = json.loads(base)
        print(f"res: {res} ")
        # 解析 JSON
        return res


def is_base64(s):
    try:
        # 尝试解码字符串
        if isinstance(s, str):
            # 将字符串编码为字节
            s = s.encode('utf-8')
        base64.b64decode(s, validate=True)
        return True
    except Exception as e:
        print(e)
        return False


def check_vmess_connection(link):
    try:
        # 创建 TCP 连接
        server = link['add']
        port = link['port']
        with socket.create_connection((server, int(port)), timeout=10) as sock:
            print(f"成功连接到服务器: {server}:{port}")
            return True
    except Exception as e:
        print(f"无法连接到服务器: {server}:{port}, 错误信息: {e}")
        return False


# 示例 vmess 链接
vmess_link = "vmess://eyJ2IjoiMiIsInBzIjoiWW91dHViZemhuuS4sOi1hOa6kCAgTm9fc3RyMjE1IiwiYWRkIjoiMjEzLjEwOS4yMDUuNjMiLCJwb3J0IjoiMjA4MiIsImlkIjoiNWYzZjA5YWQtODljYi00ZTk0LWE3YWQtYWE4MjM5OTEzNTU1IiwiYWlkIjoiMCIsInNjeSI6ImF1dG8iLCJuZXQiOiJ3cyIsInR5cGUiOiJub25lIiwiaG9zdCI6ImlwMTguNjkyOTE5OC54eXoiLCJwYXRoIjoiL2dpdGh1Yi5jb20vQWx2aW45OTk5IiwidGxzIjoiIiwic25pIjoiaXAxOC42OTI5MTk4Lnh5eiIsImFscG4iOiIiLCJmcCI6IiJ9"

tes = get_vless_from_des('https://drive.google.com/uc?export=download&id=1VUnbX2wBT7V9fQMfXWlgj1lt_npvUJfN')
if tes:
    share_links = base64.b64decode(tes).decode('utf-8').splitlines()
    for i in share_links:
        # 解码并解析链接
        if "vmess" in i:
            print(f"{i}\n")
            config = decode_vmess(i)
            # 检查连接
            is_valid = check_vmess_connection(config)
            print(f" {i} 链接有效性: {is_valid}")
