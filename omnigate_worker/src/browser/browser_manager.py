"""浏览器管理器：负责 nodriver 的启动与安全关闭、指纹注入。"""

from contextlib import asynccontextmanager
from inspect import isawaitable, signature
import asyncio
import random
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any
import logging

from src.config.config import get_settings



logger = logging.getLogger(__name__)


def get_random_fingerprint() -> dict[str, Any]:
    fingerprints = [
        {
            "name": "chrome_win",
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "width": 1366,
            "height": 768,
            "accept_language": "en-US,en;q=0.9",
            "platform": "Win32",
            "hardware_concurrency": 8,
            "device_memory": 8,
        },
        {
            "name": "chrome_mac",
            "user_agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            "width": 1440,
            "height": 900,
            "accept_language": "en-US,en;q=0.9",
            "platform": "MacIntel",
            "hardware_concurrency": 8,
            "device_memory": 8,
        },
    ]
    return random.choice(fingerprints)

class BrowserManager:
    """统一封装浏览器资源的生命周期。"""

    def __init__(self) -> None:
        self._browser: Any | None = None
        self._runtime_user_data_dir: str | None = None
        self._cleanup_user_data_dir: bool = False
        self._cleanup_bg_tasks: set[asyncio.Task[Any]] = set()

    async def start(self) -> Any:
        """启动浏览器实例。"""
        import nodriver as uc

        settings = get_settings()
        supported_params = signature(uc.start).parameters
        kwargs: dict[str, Any] = {"headless": settings.BROWSER_HEADLESS}

        # 1. 抽取一套成体系的随机指纹
        fp = get_random_fingerprint()
        logger.info(f"正在应用浏览器指纹: {fp['name']}")

        browser_args = [
            arg.strip() for arg in settings.BROWSER_ARGS.split(",")
            if arg.strip() and not arg.strip().startswith("--headless")
        ]

        # 2. 注入指纹相关的启动参数 (UA, 分辨率, 语言)
        browser_args.append(f"--user-agent={fp['user_agent']}")
        browser_args.append(f"--window-size={fp['width']},{fp['height']}")
        browser_args.append(f"--lang={fp['accept_language'].split(',')[0]}")
        browser_args.append(f"--accept-lang={fp['accept_language']}")

        if "browser_args" in supported_params:
            kwargs["browser_args"] = browser_args
        if settings.BROWSER_PROXY and "proxy" in supported_params:
            kwargs["proxy"] = settings.BROWSER_PROXY
        runtime_user_data_dir, should_cleanup = self._resolve_runtime_user_data_dir(
            configured_user_data_dir=settings.BROWSER_USER_DATA_DIR,
            supported_params=supported_params,
        )
        if runtime_user_data_dir and "user_data_dir" in supported_params:
            kwargs["user_data_dir"] = runtime_user_data_dir
        if "sandbox" in supported_params:
            kwargs["sandbox"] = settings.BROWSER_SANDBOX

        self._runtime_user_data_dir = runtime_user_data_dir
        self._cleanup_user_data_dir = should_cleanup
        try:
            self._browser = await uc.start(**kwargs)

            # 3. 【核心风控绕过】深度注入底层特征，防止 Google 通过 JS 刺探出真实硬件
            await self._inject_navigator_fingerprint(self._browser, fp)
        except Exception:
            # 启动失败时也要清理本次任务的临时目录，避免垃圾文件堆积
            await self._cleanup_runtime_user_data_dir()
            raise

        return self._browser

    async def close(self) -> None:
        """安全关闭浏览器实例（兼容同步/异步 stop/close）。"""
        browser = self._browser
        if browser is None:
            await self._cleanup_runtime_user_data_dir()
            return

        # 先置空，避免重复关闭
        self._browser = None

        try:
            stop = getattr(browser, "stop", None)
            close = getattr(browser, "close", None)

            if callable(stop):
                result = stop()
                if isawaitable(result):
                    await result
            elif callable(close):
                result = close()
                if isawaitable(result):
                    await result
        except Exception as exc:  # noqa: BLE001
            logger.warning("浏览器关闭异常: %s", exc)
        finally:
            # 每次任务完成后清理临时 user_data_dir，避免浏览器痕迹残留
            await self._cleanup_runtime_user_data_dir()

    async def _inject_navigator_fingerprint(self, browser: Any, fp: dict) -> None:
        """
        利用 CDP 协议，在任何页面执行前预注入指纹配置，
        抹平 User-Agent 和系统真实硬件底层的差异。
        """
        import nodriver.cdp.page as page

        script = f"""
        (() => {{
            Object.defineProperty(navigator, 'platform', {{
                get: () => '{fp["platform"]}'
            }});
            Object.defineProperty(navigator, 'hardwareConcurrency', {{
                get: () => {fp["hardware_concurrency"]}
            }});
            Object.defineProperty(navigator, 'deviceMemory', {{
                get: () => {fp["device_memory"]}
            }});
        }})();
        """

        try:
            command = page.add_script_to_evaluate_on_new_document(source=script)

            # 💡 核心修改：获取主标签页，并将命令发送给这个标签页
            # nodriver 中，browser 对象通常有 main_tab 属性，或者你可以取 browser.tabs[0]
            tab = browser.main_tab

            # 使用 tab 级别的连接发送指令
            await tab.send(command)

            logger.info("底层硬件特征 (Platform/RAM/CPU) 深度注入成功")
        except Exception as e:
            logger.error(f"指纹深度注入失败: {e}")

    @asynccontextmanager
    async def lifespan(self):
        """以上下文方式使用浏览器，自动做启动/释放。"""
        browser = await self.start()
        try:
            yield browser
        finally:
            await self.close()

    def _resolve_runtime_user_data_dir(
        self,
        configured_user_data_dir: str | None,
        supported_params: dict[str, Any],
    ) -> tuple[str | None, bool]:
        """
        解析本次浏览器 user_data_dir：
        - 如果已配置固定目录：使用固定目录，不自动删除
        - 如果未配置：创建本次任务独享临时目录，任务结束后删除
        """
        if "user_data_dir" not in supported_params:
            return None, False

        configured = (configured_user_data_dir or "").strip()
        if configured:
            return configured, False

        runtime_dir = tempfile.mkdtemp(prefix="omnigate_nodriver_")
        logger.info("创建浏览器临时目录: %s", runtime_dir)
        return runtime_dir, True

    async def _cleanup_runtime_user_data_dir(self) -> None:
        path = self._runtime_user_data_dir
        should_cleanup = self._cleanup_user_data_dir

        # 先重置状态，避免重复清理
        self._runtime_user_data_dir = None
        self._cleanup_user_data_dir = False

        if not should_cleanup or not path:
            return

        normalized_path = str(Path(path))
        if not os.path.exists(normalized_path):
            return

        # Chrome 退出后短时间内可能仍有句柄活动，先做短重试。
        removed, _ = await self._remove_dir_with_retries(
            normalized_path,
            attempts=6,
            initial_delay=0.2,
        )
        if removed:
            logger.info("已删除浏览器临时目录: %s", normalized_path)
            return

        # 若 close 刚返回时目录仍被占用，后台继续做更长时间重试，避免主流程阻塞。
        self._schedule_async_cleanup(normalized_path)

    async def _remove_dir_with_retries(
        self,
        path: str,
        attempts: int,
        initial_delay: float,
    ) -> tuple[bool, Exception | None]:
        last_error: Exception | None = None
        for attempt in range(1, max(attempts, 1) + 1):
            try:
                shutil.rmtree(path)
                return True, None
            except FileNotFoundError:
                return True, None
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if not os.path.exists(path):
                    return True, None
                await asyncio.sleep(initial_delay * attempt)
        return False, last_error

    def _schedule_async_cleanup(self, path: str) -> None:
        task = asyncio.create_task(self._cleanup_dir_background(path))
        self._cleanup_bg_tasks.add(task)
        task.add_done_callback(self._cleanup_bg_tasks.discard)

    async def _cleanup_dir_background(self, path: str) -> None:
        removed, last_error = await self._remove_dir_with_retries(
            path,
            attempts=20,
            initial_delay=0.5,
        )
        if removed:
            logger.info("浏览器临时目录已延迟清理: %s", path)
            return
        logger.warning("删除浏览器临时目录失败: %s | error=%s", path, last_error)
