"""CLI 入口：提供 validate / run / gui 命令。"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


@app.command("validate")
def validate_cmd(path: Path) -> None:
    """校验塔防脚本 JSON 是否符合 Schema。"""
    from nzfz_executor.script.loader import ScriptLoader
    from nzfz_executor.script.validator import ScriptValidator

    loader = ScriptLoader()
    data = loader.load(path)
    validator = ScriptValidator()
    errors = validator.validate(data)
    if errors:
        for e in errors:
            console.print(f"[red]{e.get('path', '/')}[/red] {e.get('message', '')}")
        raise typer.Exit(code=1)
    console.print("[green]校验通过[/green]", path.resolve())


@app.command("run")
def run_cmd(
    path: Path,
    dry_run: bool = typer.Option(False, "--dry-run", help="只加载与校验，不执行游戏操作"),
    title_keyword: str = typer.Option("逆战", "--title", help="游戏窗口标题关键字"),
) -> None:
    """加载并执行塔防自动化脚本。"""
    from nzfz_executor.script.loader import ScriptLoader
    from nzfz_executor.script.validator import ScriptValidator

    loader = ScriptLoader()
    data = loader.load(path)
    validator = ScriptValidator()
    errors = validator.validate(data)
    if errors:
        for e in errors:
            console.print(f"[red]{e.get('path', '/')}[/red] {e.get('message', '')}")
        raise typer.Exit(code=1)
    if dry_run:
        console.print("[green]dry-run:[/green] 已加载并校验，未执行游戏操作。", path.resolve())
        return
    console.print("[yellow]run[/yellow] 游戏内执行尚未实现。")


@app.command("gui")
def gui_cmd() -> None:
    """启动可视化 GUI 界面。"""
    import sys
    from pathlib import Path

    from PySide6.QtWidgets import QApplication
    from nzfz_executor.ui.main_window import MainWindow

    app = QApplication(sys.argv)

    qss_path = Path(__file__).resolve().parent.parent.parent / "assets" / "style.qss"
    if qss_path.is_file():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
    else:
        alt_path = Path.cwd() / "assets" / "style.qss"
        if alt_path.is_file():
            app.setStyleSheet(alt_path.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


def main() -> None:
    """CLI 主入口。"""
    app()