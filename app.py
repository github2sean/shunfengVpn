from datetime import datetime

from flask import Flask, current_app, render_template, redirect
import os
from main import from_youtube, logger

app = Flask(__name__, template_folder='templates', static_folder='assets')


def get_latest_file(directory):
    """获取目录下最新的文件"""
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    # 按修改时间降序排序，取前4个
    latest_files = sorted(files,
                          key=lambda f: datetime.strptime(f.replace('.txt', '').replace('.yaml', '').split('_A_')[-1],
                                                          '%Y-%m-%d %H-%M-%S')
                          , reverse=True)
    return latest_files


@app.route("/", methods=['GET', 'POST'])
def list_latest_files():
    # 获取项目根目录
    root_dir = current_app.root_path  # 或 os.path.dirname(current_app.instance_path)

    # 获取最新文件路径
    latest_file = get_latest_file(root_dir + os.sep + 'assets')
    if not latest_file:
        return "No files found in the directory.", 404

    # 返回文件（自动处理下载）
    return render_template('index.html', files=latest_file)


@app.route("/down", methods=['GET', 'POST'])
def index():
    try:
        from_youtube()
        return redirect('/')
    except Exception as e:
        logger.error(e)
        return str(e), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5088, debug=True)
