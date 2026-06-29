"""调度器 — 管理心跳和扫描的定时循环"""
import logging
import signal
import sys
import time
from threading import Event, Thread

from .config import Config
from .pve_client import PVEClient
from .scanner import scan_full
from .uploader import Uploader

logger = logging.getLogger(__name__)


class Scheduler:
    """Agent 调度器 — 心跳 + 扫描 + 任务检查"""

    def __init__(self, config: Config):
        self.config = config
        self.uploader = Uploader(config.platform_url)
        self.pve = PVEClient(
            config.pve_api_endpoint,
            config.pve_username,
            config.pve_password,
        )
        self._stop_event = Event()
        self._running = False

    def start(self):
        """启动调度器"""
        logger.info("Starting agent scheduler...")
        self._running = True

        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # 先认证 PVE
        logger.info("Authenticating with PVE...")
        self.pve.authenticate()

        # 启动心跳线程
        heartbeat_thread = Thread(target=self._heartbeat_loop, daemon=True)
        heartbeat_thread.start()

        # 主循环：扫描
        self._scan_loop()

    def stop(self):
        """停止调度器"""
        logger.info("Stopping agent scheduler...")
        self._running = False
        self._stop_event.set()

    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}")
        self.stop()
        sys.exit(0)

    def _heartbeat_loop(self):
        """心跳循环"""
        interval = self.config.heartbeat_interval
        logger.info(f"Heartbeat loop started (interval: {interval}s)")

        while self._running:
            try:
                self.uploader.heartbeat(
                    self.config.agent_id,
                    status="online",
                )
                logger.debug("Heartbeat sent")
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")

            self._stop_event.wait(interval)

    def _scan_loop(self):
        """扫描循环"""
        interval = self.config.scan_interval
        logger.info(f"Scan loop started (interval: {interval}s)")

        while self._running:
            try:
                self._do_scan()
            except Exception as e:
                logger.error(f"Scan failed: {e}")

            logger.info(f"Next scan in {interval}s...")
            self._stop_event.wait(interval)

    def _do_scan(self):
        """执行一次扫描并上传"""
        logger.info("=== Starting scan ===")

        # 通知心跳：正在扫描
        try:
            self.uploader.heartbeat(
                self.config.agent_id,
                status="online",
                current_task="scanning",
            )
        except Exception:
            pass

        # 采集数据
        scan_data = scan_full(self.pve)

        # 上传数据
        logger.info("Uploading scan data...")
        result = self.uploader.upload_scan(
            self.config.agent_id,
            self.config.cluster_id,
            scan_data,
        )
        logger.info(f"Upload complete: {result}")

        # 检查下发任务
        self._check_tasks()

        logger.info("=== Scan complete ===")

    def _check_tasks(self):
        """检查平台下发的任务"""
        try:
            tasks = self.uploader.get_tasks(self.config.agent_id)
            for task in tasks:
                logger.info(f"Received task: {task}")
                # 后续可扩展任务类型处理
        except Exception as e:
            logger.warning(f"Failed to check tasks: {e}")

    def run_once(self):
        """执行单次扫描（不启动循环）"""
        logger.info("Running single scan...")
        self.pve.authenticate()
        self._do_scan()
        logger.info("Single scan complete")
