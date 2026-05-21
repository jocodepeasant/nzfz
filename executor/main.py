"""应用入口模块，负责配置日志、加载 QSS 样式并启动 GUI 主循环。"""

import sys
import logging
from pathlib import Path

# main.py 位于 executor/ 子目录，nzfz_executor 包在工作区根目录 →
# 需将工作区根加入 sys.path 以解析包导入
_sys_root = Path(__file__).resolve().parent.parent
if str(_sys_root) not in sys.path:
    sys.path.insert(0, str(_sys_root))

from PySide6.QtWidgets import QApplication
from nzfz_executor.ui.main_window import MainWindow

logger = logging.getLogger(__name__)
"""模块级日志记录器"""


def main() -> None:
    """应用主入口函数。

    依次完成以下初始化流程：
    1. 创建 QApplication 实例
    2. 加载 QSS 样式表
    3. 创建并显示主窗口
    4. 进入 Qt 事件主循环
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    app = QApplication(sys.argv)

    qss_path = Path(__file__).parent / "assets" / "style.qss"
    """QSS 样式表文件路径"""

    if qss_path.exists():
        qss_content = qss_path.read_text(encoding="utf-8")
        app.setStyleSheet(qss_content)
        logger.info("QSS 样式表加载成功: %s", qss_path)
    else:
        logger.warning("QSS 样式表文件不存在: %s，降级使用默认样式", qss_path)

    window = MainWindow()
    """主窗口实例"""
    window.show()

    logger.info("GUI 主循环已启动")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()