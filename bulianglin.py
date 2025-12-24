# coding:utf-8
import argparse
import logging
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from urllib.parse import urlparse

import cv2
import numpy as np
import requests
from pyzbar.pyzbar import decode, ZBarSymbol

# 脚本说明：读取页面上的二维码保存连接和图片
# 发送请求
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
youtuber = 'bulianglin'
youtube = 'https://www.youtube.com/watch?v='
stream_id = ''
url_prefix = f'https://www.youtube.com/@{youtuber}/streams'
# 单位s
execute_interval = 60
max_retries = 3
# 单位分钟
execute_time = 10*60
list_num = 10
output_dir = "qr_codes"

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('qr_scanner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def generate_whole_url():
    req = requests.get(url_prefix, headers=headers, timeout=10)
    logger.info(f'url================{url_prefix}')
    if req.status_code == 200:
        res = req.text
        match = re.search(r'videoId":"([^"]+)', res)
        if match is not None:
            logger.info(f'url================{youtube + match.group(1)}')
            return youtube + match.group(1)
    return None


def check_dependencies():
    """检查必要的依赖工具"""
    dependencies = {
        'yt-dlp': 'yt-dlp --version',  # youtube-dl的现代化分支
        'ffmpeg': 'ffmpeg -version',
        'ffprobe': 'ffprobe -version'
    }

    missing = []
    for name, cmd in dependencies.items():
        try:
            subprocess.run(cmd.split(), capture_output=True, check=True)
            logger.info(f"✓ {name} 已安装")
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append(name)
            logger.error(f"✗ {name} 未安装")

    if missing:
        logger.error(f"缺少依赖: {missing}")
        logger.info("\n请安装依赖:")
        logger.info("sudo apt update")
        logger.info("sudo apt install -y ffmpeg python3-pip")
        logger.info("pip3 install yt-dlp opencv-python pillow pyzbar")
        if 'yt-dlp' in missing:
            logger.info("或者: sudo apt install python3-yt-dlp")
        sys.exit(1)


class YouTubeStreamQRScanner:
    def __init__(self, url, interval=execute_interval, output_dir=output_dir,
                 quality="best", max_retries=max_retries):
        """
        初始化YouTube流QR码扫描器

        Args:
            url: YouTube直播URL
            interval: 截图间隔（秒）
            output_dir: 输出目录
            quality: 视频质量（best, worst, 720p等）
            max_retries: 最大重试次数
        """
        self.url = url
        self.interval = interval
        self.output_dir = output_dir
        self.quality = quality
        self.max_retries = max_retries
        self.running = False

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 记录已识别的二维码
        self.recognized_codes = set()

        # 临时文件目录
        self.temp_dir = tempfile.mkdtemp(prefix="youtube_qr_")
        logger.info(f"临时目录: {self.temp_dir}")

        # 检查依赖
        check_dependencies()

    def get_stream_url(self):
        """
        获取YouTube直播流的直接URL

        Returns:
            视频流URL，如果失败返回None
        """
        try:
            logger.info(f"正在获取流信息: {self.url}")

            # 使用yt-dlp获取流信息
            cmd = [
                'yt-dlp',
                '--cookies', 'bnl_cookies.txt',
                '-f', f'best[height<=?1080]',  # 选择最佳质量，最高1080p
                '--get-url',
                '--no-check-certificate',
                self.url
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                stream_url = result.stdout.strip()
                if stream_url and stream_url.startswith('http'):
                    logger.info(f"成功获取流URL")
                    return stream_url
                else:
                    logger.error("无法解析流URL")
                    return None
            else:
                logger.error(f"获取流URL失败: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error("获取流URL超时")
            return None
        except Exception as e:
            logger.error(f"获取流URL时出错: {e}")
            return None

    def capture_frame(self, stream_url, output_path):
        """
        从视频流捕获一帧

        Args:
            stream_url: 视频流URL
            output_path: 输出图像路径

        Returns:
            bool: 是否成功
        """
        try:
            # 使用ffmpeg捕获一帧
            cmd = [
                'ffmpeg',
                '-y',  # 覆盖输出文件
                '-i', stream_url,
                '-frames:v', '1',  # 只捕获一帧
                '-q:v', '2',  # 高质量JPEG
                '-loglevel', 'error',  # 减少日志输出
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            logger.info(f'捕获帧结果{result}')
            if result.returncode == 0:
                # 检查文件是否有效
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    return True
                else:
                    logger.warning("捕获的帧文件无效")
                    return False
            else:
                logger.error(f"捕获帧失败: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("捕获帧超时")
            return False
        except Exception as e:
            logger.error(f"捕获帧时出错: {e}")
            return False

    def capture_frame_alternative(self, stream_url, output_path):
        """
        备选方案：使用opencv直接读取视频流
        """
        try:
            # 使用OpenCV捕获视频帧
            cap = cv2.VideoCapture(stream_url)

            if not cap.isOpened():
                logger.error("无法打开视频流")
                return False

            # 读取一帧
            ret, frame = cap.read()
            cap.release()

            if ret and frame is not None:
                # 保存图像
                cv2.imwrite(output_path, frame)
                logger.info(f"成功捕获帧: {output_path}")
                return True
            else:
                logger.error("无法从视频流读取帧")
                return False

        except Exception as e:
            logger.error(f"OpenCV捕获帧失败: {e}")
            return False

    def sanitize_filename(self, text, max_length=400):
        """清理文本以用作文件名"""
        try:
            parsed = urlparse(text)
            if parsed.scheme and parsed.netloc:
                safe_text = f"{parsed.netloc}_{parsed.path}"
            else:
                safe_text = text
        except:
            safe_text = text

        # 移除非法字符
        safe_text = re.sub(r'[<>:"/\\|?*]', '_', safe_text)
        safe_text = re.sub(r'\s+', '_', safe_text)

        # 限制长度
        if len(safe_text) > max_length:
            safe_text = safe_text[:max_length]

        if len(safe_text) < 5:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_text = f"qr_{timestamp}_{safe_text}"

        return safe_text.strip('_')

    def detect_qr_codes(self, image_path):
        """
        在图像中检测QR码

        Args:
            image_path: 图像文件路径

        Returns:
            QR码数据列表
        """
        try:
            # 读取图像
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"无法读取图像: {image_path}")
                return []

            # 增加对比度和亮度调整
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)  # 增强对比度

            # 尝试不同的阈值处理
            _, thresh1 = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            _, thresh2 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 多模式检测
            decoded_objects = decode(gray, symbols=[ZBarSymbol.QRCODE])
            if not decoded_objects:
                decoded_objects = decode(thresh1, symbols=[ZBarSymbol.QRCODE])
            if not decoded_objects:
                decoded_objects = decode(thresh2, symbols=[ZBarSymbol.QRCODE])

            results = []
            for obj in decoded_objects:
                try:
                    data = obj.data.decode('utf-8')
                    results.append(data)
                    logger.info(f"检测到QR码: {data[:100]}...")
                except:
                    logger.warning("无法解码QR码数据")
                    continue

            return results

        except Exception as e:
            logger.error(f"QR码检测失败: {e}")
            return []

    def save_qr_image(self, original_image_path, qr_data):
        """
        保存QR码图像

        Args:
            original_image_path: 原始图像路径
            qr_data: QR码数据

        Returns:
            保存的文件路径
        """
        try:
            # 生成安全的文件名
            safe_name = self.sanitize_filename(qr_data)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
            # 构建文件名
            filename = f"qr_{safe_name}_A_{current_time}.png"
            if len(filename) > 150:
                filename = f"qr_{timestamp}.png"

            # 目标路径
            filepath = os.path.join(self.output_dir, filename)

            # 复制原始图像
            import shutil
            shutil.copy2(original_image_path, filepath)

            logger.info(f"QR码图像已保存: {filepath}")

            # 记录已保存的QR码
            self.recognized_codes.add(qr_data)

            return filepath

        except Exception as e:
            logger.error(f"保存QR码图像失败: {e}")
            return None

    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            if os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
                logger.info(f"已清理临时目录: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")

    def signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info("收到停止信号，正在清理...")
        self.running = False
        self.cleanup_temp_files()
        sys.exit(0)

    def run(self, duration=execute_time, max_captures=100):
        """
        运行QR码扫描

        Args:
            duration: 运行总时长（秒）
            max_captures: 最大截图次数

        Returns:
            bool: 是否成功
        """
        # 设置信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        try:
            # 获取视频流URL
            stream_url = self.get_stream_url()
            if not stream_url:
                logger.error("无法获取视频流URL，请检查URL和网络连接")
                return False

            logger.info("开始扫描QR码...")
            logger.info(f"截图间隔: {self.interval}秒")
            logger.info(f"输出目录: {os.path.abspath(self.output_dir)}")
            logger.info("按Ctrl+C停止扫描")

            self.running = True
            start_time = time.time()
            capture_count = 0
            consecutive_failures = 0
            max_consecutive_failures = 5

            while self.running:
                # 检查是否达到限制
                if duration and (time.time() - start_time) > duration:
                    logger.info(f"达到运行时长限制: {duration}秒")
                    break

                if max_captures and capture_count >= max_captures:
                    logger.info(f"达到最大截图次数: {max_captures}")
                    break

                try:
                    # 生成临时文件名
                    temp_image = os.path.join(self.temp_dir, f"frame_{capture_count:06d}.jpg")

                    # 捕获帧
                    logger.info(f"正在捕获第{capture_count + 1}帧...")

                    # 尝试第一种方法
                    success = self.capture_frame(stream_url, temp_image)

                    # 如果失败，尝试第二种方法
                    if not success:
                        logger.warning("第一种方法失败，尝试备选方案...")
                        success = self.capture_frame_alternative(stream_url, temp_image)

                    if success:
                        capture_count += 1
                        consecutive_failures = 0

                        # 检测QR码
                        qr_codes = self.detect_qr_codes(temp_image)

                        # 处理检测到的QR码
                        for qr_data in qr_codes:
                            if qr_data in self.recognized_codes:
                                logger.info(f"QR码已识别过: {qr_data[:50]}...")
                                continue

                            # 保存QR码图像
                            self.save_qr_image(temp_image, qr_data)

                        # 删除临时文件以节省空间
                        # if os.path.exists(temp_image):
                        #     os.remove(temp_image)

                    else:
                        consecutive_failures += 1
                        logger.warning(f"捕获帧失败 ({consecutive_failures}/{max_consecutive_failures})")

                        if consecutive_failures >= max_consecutive_failures:
                            logger.error("连续失败次数过多，停止扫描")
                            break

                    # 等待下一个周期
                    logger.info(f"等待 {self.interval} 秒...")
                    time.sleep(self.interval)

                except KeyboardInterrupt:
                    logger.info("用户中断扫描")
                    break
                except Exception as e:
                    logger.error(f"扫描过程中发生错误: {e}")
                    time.sleep(self.interval)

            logger.info(f"扫描完成。总共捕获{capture_count}帧，识别到{len(self.recognized_codes)}个不同的QR码")

            # 输出总结
            if self.recognized_codes:
                logger.info("\n识别到的QR码链接:")
                for code in self.recognized_codes:
                    logger.info(f"  - {code}")

            return True

        except Exception as e:
            logger.error(f"运行失败: {e}")
            return False
        finally:
            self.cleanup_temp_files()


class YouTubeDirectScanner:
    """
    直接使用YouTube数据API的简化版本
    需要安装pytube
    """

    def __init__(self, url, interval=execute_interval, output_dir=output_dir):
        self.url = url
        self.interval = interval
        self.output_dir = output_dir
        self.recognized_codes = set()

        os.makedirs(output_dir, exist_ok=True)

    def run(self):
        """简单版本，使用pytube获取流"""
        try:
            from pytube import YouTube
            import io

            yt = YouTube(self.url)
            stream = yt.streams.filter(progressive=True, file_extension='mp4').first()

            if not stream:
                logger.error("无法获取视频流")
                return False

            logger.info(f"找到视频流: {stream.resolution}")

            # 这里需要更复杂的处理来捕获帧
            # 实际实现需要下载视频片段并处理

            logger.warning("此方法需要更多开发，推荐使用主版本")
            return False

        except ImportError:
            logger.error("需要安装pytube: pip install pytube")
            return False
        except Exception as e:
            logger.error(f"pytube版本失败: {e}")
            return False


def install_dependencies():
    """安装必要的依赖"""
    print("正在安装依赖...")

    # 更新包列表
    subprocess.run(['sudo', 'apt', 'update'], check=False)

    # 安装系统依赖
    dependencies = [
        'ffmpeg',
        'libzbar0',
        'libsm6',
        'libxext6',
        'libxrender-dev',
        'libgl1-mesa-glx'
    ]

    for dep in dependencies:
        print(f"安装 {dep}...")
        subprocess.run(['sudo', 'apt', 'install', '-y', dep], check=False)

    # 安装Python包
    python_packages = [
        'yt-dlp',
        'opencv-python',
        'pyzbar',
    ]

    for pkg in python_packages:
        print(f"安装 {pkg}...")
        subprocess.run(['pip3', 'install', pkg], check=False)

    print("依赖安装完成！")


def main():
    parser = argparse.ArgumentParser(description='YouTube直播QR码自动扫描器（服务器版）')
    parser.add_argument('-u', '--url', help='YouTube直播URL', default=generate_whole_url())
    parser.add_argument('-i', '--interval', type=int, default=execute_interval,
                        help='截图间隔（秒），默认5秒')
    parser.add_argument('-o', '--output', default=output_dir,
                        help='输出目录，默认qr_codes')
    parser.add_argument('-d', '--duration', type=int, default=execute_time,
                        help='运行总时长（秒）')
    parser.add_argument('-m', '--max-captures', type=int, default=100,
                        help='最大截图次数')
    parser.add_argument('--install', action='store_true',
                        help='安装必要依赖')
    parser.add_argument('--simple', action='store_true',
                        help='使用简化版本（需要pytube）')

    args = parser.parse_args()

    if args.install:
        install_dependencies()
        return

    # 选择扫描器版本
    if args.simple:
        scanner = YouTubeDirectScanner(
            url=args.url,
            interval=args.interval,
            output_dir=args.output
        )
    else:
        scanner = YouTubeStreamQRScanner(
            url=args.url,
            interval=args.interval,
            output_dir=args.output
        )

    # 运行扫描
    success = scanner.run(
        duration=args.duration,
        max_captures=args.max_captures
    )

    if success:
        print(f"\n扫描完成！QR码图像保存在: {os.path.abspath(args.output)}")
        if scanner.recognized_codes:
            print("\n识别到的QR码链接:")
            for code in scanner.recognized_codes:
                print(f"  - {code}")
    else:
        print("扫描失败，请检查日志文件: qr_scanner.log")


if __name__ == "__main__":
    main()

    # generate_whole_url()
