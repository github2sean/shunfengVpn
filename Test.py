import datetime
import os
import time
import urllib


def get_folder_size(path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


def list_files_and_sizes(path):
    items = []
    total_size = 0
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path):
            item_size = get_folder_size(item_path)
            item_type = '文件夹'
        else:
            item_size = os.path.getsize(item_path)
            item_type = '文件'
        items.append((item_path, item_size, item_type))
        total_size += item_size

    # 按大小排序
    items.sort(key=lambda x: x[1], reverse=True)

    for item in items:
        if item[2] == '文件夹':
            print(f"文件夹: {item[0]}, 大小: {item[1] / (1024 * 1024):.2f} MB")
        else:
            print(f"文件: {item[0]}, 大小: {item[1] / 1024:.2f} KB")
    print(f"总大小: {total_size / (1024 * 1024):.2f} MB")


# 指定路径
path = "C://Program Files//WindowsApps"
# list_files_and_sizes(path)

if __name__ == '__main__':
    now = datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S')
    # now2 = urllib.parse.unquote(now)
    # print(now, now2)
    str = 'https%3A%2F%2Fskill-note.blogspot.com%2F2024%2F10%2F28.html_A_ IOS 苹果小火箭专用(点击自动下载，订阅地址请右键复制链接地址)_A_1Xb3YhNbhf2tuNda6KU8X2ndXmOg1GCak_A_2025-07-09 20-36-19.txt'
    list2 = str.split('_A_')
    print(str.replace('.txt', '.yaml', ''))
    # # 确保目录存在
    # os.makedirs(os.path.dirname(str), exist_ok=True)
    # with open(str, 'w') as f:
    #     f.write(str)
