"""执行器主窗口模块，提供包含 QTabWidget 页签框架的可视化主界面。"""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget
from nzfz_executor.ui.tabs.game_connect import GameConnectTab


class MainWindow(QMainWindow):
    """执行器主窗口，包含 QTabWidget 页签框架。"""

    def __init__(self) -> None:
        """初始化主窗口：设置标题与默认尺寸，创建页签控件。"""
        super().__init__()
        self.setWindowTitle("逆战塔防工具")
        self.resize(900, 700)

        self._tab_widget = QTabWidget()
        """页签控件，承载各功能页签"""
        self.setCentralWidget(self._tab_widget)

        self._game_connect_tab = GameConnectTab()
        """游戏连接页签"""
        self._tab_widget.addTab(self._game_connect_tab, "游戏连接")