import os

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
list_files_and_sizes(path)





