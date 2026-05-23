"""P2-03A：Windows Graphics Capture 技术验证脚本。"""

from __future__ import annotations

import argparse
import platform
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nzfz_executor.core.wgc_capture import (  # noqa: E402
    capture_hwnd_to_image,
    is_wgc_available,
    is_wgc_platform_supported,
)


def _find_hwnd_by_title(keyword: str) -> int | None:
    import win32gui

    matches: list[tuple[int, str]] = []

    def _callback(hwnd: int, _extra) -> bool:
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if keyword.lower() in title.lower():
            matches.append((hwnd, title))
        return True

    win32gui.EnumWindows(_callback, None)
    if not matches:
        return None
    matches.sort(key=lambda item: len(item[1]))
    hwnd, title = matches[0]
    print(f"匹配窗口: hwnd={hwnd}, title={title!r}")
    return hwnd


def _describe_window(hwnd: int) -> None:
    import win32gui

    title = win32gui.GetWindowText(hwnd)
    visible = win32gui.IsWindowVisible(hwnd)
    minimized = win32gui.IsIconic(hwnd)
    rect = win32gui.GetWindowRect(hwnd)
    print(
        f"窗口信息: title={title!r}, visible={visible}, "
        f"minimized={minimized}, rect={rect}",
    )


def _build_output_path(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_dir / f"wgc_capture_{stamp}.png"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Windows Graphics Capture 技术验证（P2-03A）",
    )
    parser.add_argument("--hwnd", type=int, help="目标窗口句柄")
    parser.add_argument("--title", type=str, help="窗口标题关键词")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "output",
        help="PNG 输出目录",
    )
    args = parser.parse_args()

    if not args.hwnd and not args.title:
        parser.error("必须指定 --hwnd 或 --title")

    print("=== WGC Probe 环境 ===")
    print(f"OS: {platform.platform()}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform supported: {is_wgc_platform_supported()}")
    print(f"WGC available: {is_wgc_available()}")

    if not is_wgc_available():
        print("ERROR: Windows Graphics Capture 当前不可用")
        return 1

    hwnd = args.hwnd
    if hwnd is None:
        assert args.title is not None
        hwnd = _find_hwnd_by_title(args.title)
        if hwnd is None:
            print(f"ERROR: 未找到标题包含 {args.title!r} 的窗口")
            return 1

    _describe_window(hwnd)

    import win32gui

    if not win32gui.IsWindow(hwnd):
        print("ERROR: hwnd 无效")
        return 1
    if not win32gui.IsWindowVisible(hwnd):
        print("ERROR: 窗口不可见")
        return 1
    if win32gui.IsIconic(hwnd):
        print("ERROR: 窗口已最小化（预期失败）")
        return 1

    try:
        image = capture_hwnd_to_image(hwnd)
    except Exception as exc:
        print(f"ERROR: WGC 捕获失败: {exc}")
        return 1

    output_path = _build_output_path(args.output_dir)
    rgb_image = image.convert("RGB")
    rgb_image.save(output_path)

    print("=== 捕获结果 ===")
    print(f"尺寸: {image.width} x {image.height}")
    print(f"模式: {image.mode}")
    print(f"PNG: {output_path}")
    print("结论: WGC 单帧捕获成功，适合接入正式后端")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
