"""NewsFlow CLI — entry point.

Usage:
  newsflow run tech_daily          # run a workflow
  newsflow run tech_daily --dry-run
  newsflow list                    # list recent runs
  newsflow show <run_id>           # show run stats
  newsflow collectors              # list available collectors
  newsflow mcp                     # start MCP server
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="newsflow", add_completion=False, help="NewsFlow pipeline CLI")
console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


@app.command("run")
def cmd_run(
    workflow: str = typer.Argument(..., help="Workflow name or path to YAML"),
    hours: int = typer.Option(24, "--hours", "-h", help="Time window in hours"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip publishing"),
    sources: list[str] = typer.Option([], "--source", "-s", help="Limit to specific collectors"),
    data_dir: str = typer.Option("./data", "--data-dir"),
) -> None:
    """Execute a NewsFlow pipeline workflow."""
    from newsflow.pipeline.engine import PipelineEngine

    wf_path = _resolve_workflow(workflow)
    engine = PipelineEngine(wf_path, data_dir=data_dir)

    result = asyncio.run(
        engine.run(
            hours=hours,
            dry_run=dry_run,
            sources=sources or None,
        )
    )

    stats = result.get("stats", {})
    console.print(f"\n[bold green]✓ Run complete[/bold green]  run_id=[cyan]{result['run_id']}[/cyan]")
    console.print(
        f"  collected={stats.get('collected', 0)}"
        f"  deduped={stats.get('deduped', 0)}"
        f"  filtered={stats.get('filtered', 0)}"
        f"  tokens={stats.get('token_used', 0)}"
    )


@app.command("list")
def cmd_list(
    limit: int = typer.Option(10, "--limit", "-n"),
    data_dir: str = typer.Option("./data", "--data-dir"),
) -> None:
    """List recent pipeline runs."""
    from newsflow.storage.local import LocalStorage

    storage = LocalStorage(data_dir)
    runs = storage.list_runs(limit=limit)

    table = Table("run_id", "workflow", "collected", "filtered", "tokens")
    for r in runs:
        stats = r.get("stats", {})
        table.add_row(
            r["run_id"],
            r.get("workflow", ""),
            str(stats.get("collected", "")),
            str(stats.get("filtered", "")),
            str(stats.get("token_used", "")),
        )
    console.print(table)


@app.command("show")
def cmd_show(
    run_id: str = typer.Argument(...),
    stage: str = typer.Option("filtered", "--stage"),
    data_dir: str = typer.Option("./data", "--data-dir"),
) -> None:
    """Show items from a run."""
    from newsflow.storage.local import LocalStorage

    storage = LocalStorage(data_dir)
    items = storage.load_items(run_id, stage=stage)

    table = Table("score", "title", "source", "url")
    for item in items:
        table.add_row(
            f"{item.ai_score:.1f}" if item.ai_score else "—",
            item.title[:60],
            item.source_type.value,
            item.url[:50],
        )
    console.print(table)


@app.command("collectors")
def cmd_collectors() -> None:
    """List available collector types."""
    from newsflow.collectors.registry import list_collectors

    for name in list_collectors():
        console.print(f"  • {name}")


@app.command("mcp")
def cmd_mcp() -> None:
    """Start the MCP server (stdio transport)."""
    from newsflow.mcp.server import mcp
    mcp.run()


def _resolve_workflow(name: str) -> Path:
    p = Path(name)
    if p.exists():
        return p
    candidate = Path("config/workflows") / f"{name}.yaml"
    if candidate.exists():
        return candidate
    raise typer.BadParameter(f"Workflow '{name}' not found.")


if __name__ == "__main__":
    app()
