"""
Autonomous Systems â€” Agent Architecture CLI Entrypoint

Usage:
    python main.py --help
    python main.py run <directive>
    python main.py validate <directive>
    python main.py list-directives
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# Load .env before any module imports that rely on env vars
load_dotenv()

from orchestrator.router import Router  # noqa: E402 (post-env-load import)
from executor.tools.logging_tool import get_logger  # noqa: E402

app = typer.Typer(
    name="Agent",
    help="Autonomous Systems â€” 3-Layer Agent CLI",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()
log = get_logger(__name__)

DIRECTIVES_DIR = Path("directives")


@app.command()
def run(
    directive: str = typer.Argument(..., help="Directive filename (without .md extension)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Validate and plan without executing"),
) -> None:
    """
    Load and execute a directive through the full 3-layer pipeline.
    """
    directive_path = DIRECTIVES_DIR / f"{directive}.md"
    if not directive_path.exists():
        console.print(f"[red]Directive not found:[/red] {directive_path}")
        raise typer.Exit(code=1)

    console.print(f"\n[bold cyan]Agent Agent[/bold cyan] â€” Loading directive: [bold]{directive}[/bold]\n")

    router = Router()
    router.execute(directive_path=directive_path, dry_run=dry_run)


@app.command()
def validate(
    directive: str = typer.Argument(..., help="Directive filename (without .md extension)"),
) -> None:
    """
    Validate a directive against the required 7-section template structure.
    """
    directive_path = DIRECTIVES_DIR / f"{directive}.md"
    if not directive_path.exists():
        console.print(f"[red]Directive not found:[/red] {directive_path}")
        raise typer.Exit(code=1)

    router = Router()
    result = router.validate_directive(directive_path)

    if result.is_valid:
        console.print(f"[green]âœ“ Directive is valid:[/green] {directive}")
    else:
        console.print(f"[red]âœ— Directive has issues:[/red] {directive}")
        for issue in result.issues:
            console.print(f"  [yellow]â€¢[/yellow] {issue}")


@app.command(name="list-directives")
def list_directives() -> None:
    """
    List all available directives (excluding archived versions).
    """
    if not DIRECTIVES_DIR.exists():
        console.print(f"[red]Directives directory not found:[/red] {DIRECTIVES_DIR}")
        raise typer.Exit(code=1)

    directives = sorted(
        p for p in DIRECTIVES_DIR.glob("*.md")
        if not p.name.startswith("_")
    )

    if not directives:
        console.print("[yellow]No directives found.[/yellow]")
        return

    table = Table(title="Available Directives", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="bold")
    table.add_column("Path")

    for d in directives:
        table.add_row(d.stem, str(d))

    console.print(table)


if __name__ == "__main__":
    app()

