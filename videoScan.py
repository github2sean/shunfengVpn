import cv2
import requests
import time
import re
import threading
import queue
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import qrcode_terminal
from main import logger
import m3u8
from streamlink import Streamlink


class LiveStreamQRCodeDetector:
    def __init__(self, stream_url, frame_queue_size=100, detection_interval=1, proxy=None):
        """初始化直播二维码检测器"""
        self.stream_url = stream_url
        self.frame_queue = queue.Queue(maxsize=frame_queue_size)
        self.detection_interval = detection_interval  # 检测间隔(秒)
        self.stop_event = threading.Event()
        self.detection_results = set()
        self.qr_detector = cv2.QRCodeDetector()
        self.proxy = proxy

    def _open_stream(self):
        """尝试使用不同方法打开直播流"""
        # 检查是否为HLS流URL
        if self._is_hls_url(self.stream_url):
            return self._open_hls_stream()

        # 方法1: 直接使用OpenCV (适用于部分RTSP/HTTP流)
        cap = cv2.VideoCapture(self.stream_url)
        if cap.isOpened():
            logger.info("成功通过OpenCV直接打开流")
            return cap

        logger.error("无法打开直播流，不支持的URL格式")
        return None

    def _is_hls_url(self, url):
        """检查是否为HLS流URL"""
        return url.endswith('.m3u8') or 'manifest.googlevideo.com' in url or 'youtube.com' in url

    def _open_hls_stream(self):
        """打开HLS流"""
        try:
            # 优先使用streamlink
            logger.info("尝试使用streamlink解析HLS流...")
            session = Streamlink()

            # 设置代理
            if self.proxy:
                session.set_option("http-proxy", self.proxy)
                session.set_option("https-proxy", self.proxy)
                logger.info(f"已设置代理: {self.proxy}")

            # 特殊处理YouTube直播
            if 'youtube.com' in self.stream_url:
                # 尝试从嵌入URL提取视频ID
                video_id_match = re.search(r'youtu\.be/([^/?]+)|youtube\.com/watch\?v=([^&]+)', self.stream_url)
                if video_id_match:
                    video_id = video_id_match.group(1) or video_id_match.group(2)
                    self.stream_url = f"https://www.youtube.com/watch?v={video_id}"
                    logger.info(f"转换为YouTube视频URL: {self.stream_url}")
                else:
                    logger.warning("无法提取YouTube视频ID")

            streams = session.streams(self.stream_url)
            if not streams:
                logger.warning("无法通过streamlink找到可用流，尝试手动解析m3u8")
            else:
                # 选择最高质量的流
                stream_url = streams["best"].url
                logger.info("成功获取到流地址，尝试打开...")

                cap = cv2.VideoCapture(stream_url)
                if cap.isOpened():
                    logger.info("成功通过streamlink打开流")
                    return cap
                else:
                    logger.warning("无法通过streamlink打开流，尝试手动解析m3u8")

            # 手动解析m3u8文件
            if self.stream_url.endswith('.m3u8') or 'manifest.googlevideo.com' in self.stream_url:
                return self._parse_m3u8_stream()

        except Exception as e:
            logger.error(f"处理HLS流时出错: {str(e)}")

        return None

    def _parse_m3u8_stream(self):
        """手动解析m3u8文件"""
        try:
            logger.info("尝试手动解析m3u8文件...")
            # 设置代理
            proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None

            r = requests.get(self.stream_url, proxies=proxies, timeout=10)
            r.raise_for_status()
            print("是否有FFmpeg支持", cv2.getBuildInformation())  # 检查输出中是否有FFmpeg支持
            m3u8_obj = m3u8.loads(r.text)
            if m3u8_obj.is_variant:
                # 多层播放列表，选择最高带宽
                playlist = max(m3u8_obj.playlists, key=lambda p: p.stream_info.bandwidth)
                base_url = self.stream_url.rsplit('/', 1)[0] + '/'
                stream_url = urljoin(base_url, playlist.uri)
                logger.info(f"选择了高带宽流: {stream_url}")
            else:
                # 单层播放列表
                stream_url = self.stream_url
                logger.info(f"使用原始流地址: {stream_url}")
            playlist = m3u8.load(stream_url)
            for segment in playlist.segments:
                print(segment.uri)  # 获取TS分片地址
                logger.info("m3u8解析完成，尝试打开流...")
                cap = cv2.VideoCapture(segment.uri)
                if cap.isOpened():
                    logger.info("成功通过m3u8解析打开流")
                    return cap
                else:
                    logger.error("无法打开解析后的m3u8流")

        except Exception as e:
            logger.error(f"手动解析m3u8时出错: {str(e)}")

        return None

    def _capture_frames(self):
        """帧捕获线程函数"""
        cap = self._open_stream()

        if not cap:
            logger.error(f"无法打开直播流: {self.stream_url}")
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30  # 默认假设30fps
        frame_skip = max(1, int(fps * self.detection_interval))
        frame_count = 0

        logger.info(f"开始捕获直播帧 (假设FPS: {fps:.2f}, 检测间隔: {self.detection_interval}秒)")

        while not self.stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                logger.warning("无法读取帧，尝试重新连接...")
                time.sleep(1)  # 等待1秒后尝试重新连接
                cap.release()
                cap = self._open_stream()
                if not cap:
                    logger.error("重新连接失败，退出捕获线程")
                    break
                continue

            frame_count += 1
            if frame_count % frame_skip == 0:
                try:
                    self.frame_queue.put_nowait(frame.copy())
                except queue.Full:
                    logger.debug("帧队列已满，丢弃帧")

        cap.release()
        logger.info("帧捕获线程已停止")

    def _detect_qrcodes(self):
        """二维码检测线程函数"""
        logger.info("开始二维码检测线程")

        while not self.stop_event.is_set():
            try:
                frame = self.frame_queue.get(timeout=1)
            except queue.Empty:
                continue

            # 转换为灰度图提高检测率
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 检测二维码
            retval, decoded_info, points, straight_qrcode = self.qr_detector.detectAndDecodeMulti(gray)

            if retval:
                for i in range(len(decoded_info)):
                    if decoded_info[i] and decoded_info[i] not in self.detection_results:
                        self.detection_results.add(decoded_info[i])
                        logger.info(f"检测到新二维码: {decoded_info[i]}")
                        qrcode_terminal.draw(decoded_info[i])

            self.frame_queue.task_done()

        logger.info("二维码检测线程已停止")

    def start(self, duration=None):
        """启动检测器"""
        self.capture_thread = threading.Thread(target=self._capture_frames)
        self.detection_thread = threading.Thread(target=self._detect_qrcodes)

        self.capture_thread.daemon = True
        self.detection_thread.daemon = True

        self.capture_thread.start()
        self.detection_thread.start()

        logger.info(
            f"直播二维码检测器已启动，将持续检测{duration}秒" if duration else "直播二维码检测器已启动，按Ctrl+C停止")

        try:
            if duration:
                time.sleep(duration)
            else:
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            pass

    def stop(self):
        """停止检测器并返回结果"""
        logger.info("正在停止检测器...")
        self.stop_event.set()

        # 等待线程结束
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join(timeout=2)
        if hasattr(self, 'detection_thread'):
            self.detection_thread.join(timeout=2)

        # 清空队列
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                continue

        results = list(self.detection_results)
        logger.info(f"检测完成，共发现{len(results)}个不同的二维码")
        return results


def extract_stream_url(html_content, base_url):
    """从HTML内容中提取直播流URL"""
    soup = BeautifulSoup(html_content, 'html.parser')

    # 检查常见的直播嵌入标签
    video_tags = soup.find_all('video')
    if video_tags:
        for video in video_tags:
            source = video.find('source')
            if source and source.get('src'):
                return urljoin(base_url, source.get('src'))
            elif video.get('src'):
                return urljoin(base_url, video.get('src'))

    # 检查常见直播平台的嵌入代码
    patterns = [
        # HLS流
        r'(https?://[^"\']+\.m3u8)',
        # RTMP流
        r'rtmp://[^"\']+',
        # WebRTC相关
        r'peerjs\.js',
        # YouTube直播
        r'www\.youtube\.com/embed/([^"\']+)',
        r'youtu\.be/([^"\'?]+)',
        r'youtube\.com/watch\?v=([^&]+)',
        # Bilibili直播
        r'live\.bilibili\.com/([^"\']+)',
        # 抖音直播
        r'live\.douyin\.com/([^"\']+)',
        # 其他常见直播平台
        r'(https?://[^"\']+\.flv)',
        r'(https?://[^"\']+\.f4m)'
    ]

    for pattern in patterns:
        match = re.search(pattern, html_content)
        if match:
            return match.group(1)

    return None


def main(url, detection_time=30, proxy=None):
    """主函数：从网页提取直播流并检测二维码"""
    try:
        logger.info(f"正在请求网页: {url}")

        # 设置代理
        proxies = {"http": proxy, "https": proxy} if proxy else None

        response = requests.get(url, proxies=proxies)
        response.raise_for_status()

        stream_url = extract_stream_url(response.text, url)
        if not stream_url:
            logger.error("未能在网页中找到直播流")
            return

        logger.info(f"找到直播流: {stream_url}")

        logger.info(f"开始检测直播流中的二维码，检测时间: {detection_time}秒")
        detector = LiveStreamQRCodeDetector(stream_url, detection_interval=1, proxy=proxy)

        # 启动检测器
        detector.start(detection_time)

        # 手动调用stop()获取结果
        results = detector.stop()

        if results:
            logger.info(f"\n检测到{len(results)}个不同的二维码:")
            for i, code in enumerate(results, 1):
                print(f"\n[{i}] {code}")
        else:
            logger.info("未在直播流中检测到二维码")

    except Exception as e:
        logger.error(f"错误: {str(e)}")


if __name__ == "__main__":
    # import sys
    #
    # if len(sys.argv) < 2:
    #     print("用法: python live_stream_qrcode_detector.py <直播网页URL> [检测时间(秒)] [代理服务器地址]")
    #     print("示例: python live_stream_qrcode_detector.py https://example.com/live 60 http://127.0.0.1:7890")
    #     sys.exit(1)
    #
    # url = sys.argv[1]
    # detection_time = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    # proxy = sys.argv[3] if len(sys.argv) > 3 else None

    main('https://www.youtube.com/watch?v=cS6zS5hi1w0', 30, None)
    # main('http://devimages.apple.com/iphone/samples/bipbop/bipbopall.m3u8', 30, None)
