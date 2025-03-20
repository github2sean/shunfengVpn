import sys
import time
import requests
import json
import base64
import subprocess
import threading
import os
import datetime
from queue import Queue
from Models import Vless

import Models
from task.parse import parse_shadowsocks_link, parse_trojan_link, parse_vless_link, generate_vmess_config

# 测试用的目标 URL（可以替换为其他地址）
TEST_URL = "http://www.google.com"
DOWNLOAD_URL = "http://ipv4.download.thinkbroadband.com/100MB.zip"  # 用于下载速度测试

# 结果队列，用于存储测试结果
result_queue = Queue()
lock = threading.Lock()


def parse_vmess_link(link):
    """解析 VMess 链接"""
    if not link.startswith("vmess://"):
        raise ValueError("Invalid VMess link")

    # 去除协议头并解码
    encoded = link[8:]
    decoded = base64.b64decode(encoded).decode("utf-8")
    config = json.loads(decoded)
    config["port"] = int(config["port"])

    return config


def start_proxy(config):
    """根据配置启动代理"""
    # 将配置写入临时文件
    try:
        current_file_path = f"{os.path.dirname(os.path.abspath(__file__)) + os.sep}config.json"
        with open(current_file_path, "w") as f:
            json.dump(config, f)
        # 启动 v2ray-core 或 Xray-core
        process = subprocess.Popen(["xray", f"-config={current_file_path}"], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   text=True)
    except Exception as e:
        print("start_proxy_has_exception:", e)

    return process


def calcu_latency(proxy):
    """测试延迟"""
    try:
        start_time = time.time()
        response = requests.get(TEST_URL, proxies=proxy, timeout=500)
        latency = (time.time() - start_time) * 1000  # 转换为毫秒
        return latency
    except Exception as e:
        print(f"Latency test failed: {e}")
        return '-1ms'


def calcu_download_speed(proxy):
    """测试下载速度"""
    try:
        start_time = time.time()
        response = requests.get(DOWNLOAD_URL, proxies=proxy, stream=True, timeout=30)
        total_length = int(response.headers.get("content-length", 0))
        downloaded = 0

        for chunk in response.iter_content(chunk_size=8192):
            downloaded += len(chunk)
            if time.time() - start_time > 5:  # 最多测试 10 秒
                break

        duration = time.time() - start_time
        speed = (downloaded / duration) / 1024  # 转换为 KB/s
        return speed
    except Exception as e:
        print(f"Download speed test failed: {e}")
        return 0


def handel_link(link_param):
    """测试链接的延迟和下载速度"""
    try:
        proxy = {
            "http": "socks5://127.0.0.1:1080",  # 本地代理地址
            "https": "socks5://127.0.0.1:1080"
        }
        if link_param.startswith("vmess://"):
            config = parse_vmess_link(link_param)
            proxy_process = start_proxy(generate_vmess_config(config))

        elif link_param.startswith("ss://"):
            config = parse_shadowsocks_link(link_param)
            proxy_process = start_proxy(config)
            # 解析 Shadowsocks 链接
            pass
        elif link_param.startswith("trojan://"):
            config = parse_trojan_link(link_param)
            proxy_process = start_proxy(config)
            # 解析 Trojan 链接
            pass
        elif link_param.startswith("vless://"):
            config = parse_vless_link(link_param)
            proxy_process = start_proxy(config)
            # 解析 VLESS 链接
            pass
        else:
            raise ValueError("Unsupported link type")

        print(f"Testing link: {link_param}")

        # 测试延迟
        latency = calcu_latency(proxy)
        if latency is not None:
            print(f"Latency: {latency:.2f} ms")
        if latency != '-1ms' and latency > 0:
            # 测试下载速度
            speed = calcu_download_speed(proxy)
            if speed is not None:
                print(f"Download speed: {speed:.2f} KB/s")

            # 将结果存入队列
            link = link_param
            result_queue.put((link, latency, speed))
        # 关闭代理进程
        proxy_process.terminate()
    except Exception as e:
        print(f"Error testing link : {e}")
        result_queue.put((link_param, None, None))


def worker(link_param):
    """线程 worker 函数"""
    handel_link(link_param)


def query_vmess():
    # 计算最近一周的时间范围
    now = datetime.datetime.now()
    one_week_ago = now - datetime.timedelta(days=30)
    vless_objs = Vless.select().where((Vless.type == 4) & (Vless.is_ping == 0) & (Vless.create_time >= one_week_ago))
    return vless_objs


if __name__ == '__main__':
    # 测试链接列表
    #     "vmess://...",  # 替换为你的 VMess 链接
    #     "ss://...",  # 替换为你的 Shadowsocks 链接
    #     "trojan://...",  # 替换为你的 Trojan 链接
    #     "vless://..."  # 替换为你的 VLESS 链接
    # links = [Vless.vpn_link for Vless in query_vmess()]

    links = [
        # "vmess://eyJ2IjoiMiIsInBzIjoiWW91dHViZemhuuS4sOi1hOa6kOmmmea4rzE2NiIsImFkZCI6IjEyMC4xOTguNzEuMjE0IiwicG9ydCI6IjM1NTY1IiwiaWQiOiI0MTgwNDhhZi1hMjkzLTRiOTktOWIwYy05OGNhMzU4MGRkMjQiLCJhaWQiOiIwIiwic2N5IjoiYXV0byIsIm5ldCI6InRjcCIsInR5cGUiOiJub25lIiwiaG9zdCI6IiIsInBhdGgiOiIiLCJ0bHMiOiIiLCJzbmkiOiIiLCJhbHBuIjoiIiwiZnAiOiIifQ==",
        # "vmess://eyJ2IjoiMiIsInBzIjoiWW91dHViZemhuuS4sOi1hOa6kOe+juWbvTEyOCIsImFkZCI6InMxLmRiLWxpbmswMS50b3AiLCJwb3J0IjoiMjA5NSIsImlkIjoiNGIzNjYyNWMtYjlkOS0zZWE2LWFlZDUtODZkNjJjNzBlMTZkIiwiYWlkIjoiMCIsInNjeSI6ImF1dG8iLCJuZXQiOiJ3cyIsInR5cGUiOiJub25lIiwiaG9zdCI6IjEwMC0xMDUtOTItMTU4LnMxLmRiLWxpbmswMS50b3AiLCJwYXRoIjoiL2RhYmFpLmluMTA0LjI0Ljg5LjExIiwidGxzIjoiIiwic25pIjoiMTAwLTEwNS05Mi0xNTguczEuZGItbGluazAxLnRvcCIsImFscG4iOiIiLCJmcCI6IiJ9",
        # "vmess://eyJ2IjoiMiIsInBzIjoiWW91dHViZemhuuS4sOi1hOa6kOmmmea4rzE4MyIsImFkZCI6IjEyMC4xOTguNzEuMjE5IiwicG9ydCI6IjQ0MDE0IiwiaWQiOiI0MTgwNDhhZi1hMjkzLTRiOTktOWIwYy05OGNhMzU4MGRkMjQiLCJhaWQiOiIwIiwic2N5IjoiYXV0byIsIm5ldCI6InRjcCIsInR5cGUiOiJub25lIiwiaG9zdCI6IiIsInBhdGgiOiIiLCJ0bHMiOiIiLCJzbmkiOiIiLCJhbHBuIjoiIiwiZnAiOiIifQ==",
        "vmess://ew0KICAidiI6ICIyIiwNCiAgInBzIjogIllvdXR1YmVcdTk4N0FcdTRFMzBcdThENDRcdTZFOTBcdTk5OTlcdTZFMkYyMyIsDQogICJhZGQiOiAiMTIwLjIzMi4xNTMuNjMiLA0KICAicG9ydCI6ICI0MDEwNSIsDQogICJpZCI6ICI0MTgwNDhhZi1hMjkzLTRiOTktOWIwYy05OGNhMzU4MGRkMjQiLA0KICAiYWlkIjogIjAiLA0KICAic2N5IjogImF1dG8iLA0KICAibmV0IjogInRjcCIsDQogICJ0eXBlIjogIm5vbmUiLA0KICAiaG9zdCI6ICIiLA0KICAicGF0aCI6ICIiLA0KICAidGxzIjogIiIsDQogICJzbmkiOiAiIiwNCiAgImFscG4iOiAiIiwNCiAgImZwIjogIiINCn0=",
        "vmess://ew0KICAidiI6ICIyIiwNCiAgInBzIjogIllvdXR1YmVcdTk4N0FcdTRFMzBcdThENDRcdTZFOTBcdTk5OTlcdTZFMkYyNSIsDQogICJhZGQiOiAiMTgzLjIzNi41MS4zOCIsDQogICJwb3J0IjogIjUzOTAyIiwNCiAgImlkIjogIjQxODA0OGFmLWEyOTMtNGI5OS05YjBjLTk4Y2EzNTgwZGQyNCIsDQogICJhaWQiOiAiMCIsDQogICJzY3kiOiAiYXV0byIsDQogICJuZXQiOiAidGNwIiwNCiAgInR5cGUiOiAibm9uZSIsDQogICJob3N0IjogIiIsDQogICJwYXRoIjogIiIsDQogICJ0bHMiOiAiIiwNCiAgInNuaSI6ICIiLA0KICAiYWxwbiI6ICIiLA0KICAiZnAiOiAiIg0KfQ=="
    ]
    for link in links:
        handel_link(link)
    # 创建并启动线程
    threads = []
    for row in links:
        thread = threading.Thread(target=worker, args=(row,))
        thread.start()
        threads.append(thread)

    # 等待所有线程完成
    for thread in threads:
        thread.join()

    # 输出所有测试结果
    print("\nTest Results:")
    while not result_queue.empty():
        link, latency, speed = result_queue.get()
        print(f"Link: {link}")
        if latency is not None:
            print(f"  Latency: {latency:.2f} ms")
        if speed is not None:
            print(f"  Download speed: {speed:.2f} KB/s")
        print("-" * 40)
