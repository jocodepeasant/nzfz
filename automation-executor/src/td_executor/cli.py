from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from td_executor.script.load import load_script_file
from td_executor.script.validate import validate_script_data
from td_executor.runtime.window import find_game_window

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


@app.command("validate")
def validate_cmd(path: Path) -> None:
    """Validate a tower defense script JSON against the shared schema."""
    data = load_script_file(path)
    errors = validate_script_data(data)
    if errors:
        table = Table(title="校验失败")
        table.add_column("路径", style="cyan")
        table.add_column("说明", style="red")
        for e in errors:
            table.add_row(e.get("path", "/"), e.get("message", ""))
        console.print(table)
        raise typer.Exit(code=1)
    console.print("[green]校验通过[/green]", path.resolve())


@app.command("run")
def run_cmd(
    path: Path,
    dry_run: bool = typer.Option(False, "--dry-run", help="只加载与校验，不操作游戏"),
    title_keyword: str = typer.Option("逆战", "--title", help="游戏窗口标题关键字"),
) -> None:
    """Load script (and optionally run automation when implemented)."""
    data = load_script_file(path)
    errors = validate_script_data(data)
    if errors:
        for e in errors:
            console.print(f"[red]{e.get('path', '/')}[/red] {e.get('message', '')}")
        raise typer.Exit(code=1)
    if dry_run:
        console.print("[green]dry-run:[/green] 已加载并校验，未执行游戏操作。", path.resolve())
        return
    rect = find_game_window(title_keyword)
    if rect is None:
        console.print(f"[red]错误:[/red] 未找到标题包含 '{title_keyword}' 的游戏窗口，请确认游戏已启动。")
        raise typer.Exit(code=1)
    console.print(f"[green]已定位游戏窗口[/green] {rect}")
    console.print("[yellow]run[/yellow] 游戏内执行尚未完全实现。")


@app.command("gui")
def gui_cmd() -> None:
    """Launch the visual GUI interface."""
    from td_executor.ui.app import launch
    launch()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
