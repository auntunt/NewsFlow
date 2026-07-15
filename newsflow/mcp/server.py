"""NewsFlow — Phase 2: MCP Server (server.py)

Exposes NewsFlow pipeline as MCP tools via FastMCP.
Run: python -m newsflow.mcp.server
"""
from __future__ import annotations

import os
from pathlib import Path

from fastmcp import FastMCP

from newsflow.pipeline.engine import PipelineEngine
from newsflow.storage.local import LocalStorage

mcp = FastMCP("newsflow-mcp")

_DATA_DIR = os.getenv("DATA_DIR", "./data")
_WORKFLOW_DIR = Path("config/workflows")


def _storage() -> LocalStorage:
    return LocalStorage(_DATA_DIR)


# ── Execute tools ─────────────────────────────────────────────────────────────


@mcp.tool()
async def nf_run_workflow(
    workflow: str,
    hours: int = 24,
    dry_run: bool = False,
    sources: list[str] | None = None,
) -> dict:
    """
    Execute a full NewsFlow pipeline: collect → score → filter → (generate) → (publish).

    Args:
        workflow: workflow name (e.g. "tech_daily") or path to YAML file
        hours: time window for collecting content (default: 24)
        dry_run: if True, skip publishing
        sources: optional list to limit to specific collectors (e.g. ["hackernews"])
    """
    wf_path = _resolve_workflow(workflow)
    engine = PipelineEngine(wf_path, data_dir=_DATA_DIR)
    return await engine.run(hours=hours, dry_run=dry_run, sources=sources)


@mcp.tool()
async def nf_collect(
    sources: list[str],
    hours: int = 24,
) -> dict:
    """
    Run only the collection stage for given sources.

    Args:
        sources: collector types, e.g. ["hackernews", "github_trending", "newsnow"]
        hours: time window
    """
    from newsflow.collectors.registry import get_collector

    all_items = []
    errors = []
    for src in sources:
        try:
            collector = get_collector(src)
            items = await collector.collect(hours=hours, limit=50)
            all_items.extend(items)
        except Exception as exc:
            errors.append({"source": src, "error": str(exc)})

    return {
        "ok": True,
        "count": len(all_items),
        "errors": errors,
        "items": [i.model_dump(mode="json") for i in all_items],
    }


# ── Query tools ───────────────────────────────────────────────────────────────


@mcp.tool()
def nf_list_runs(limit: int = 10) -> dict:
    """List recent pipeline runs."""
    storage = _storage()
    return {"runs": storage.list_runs(limit=limit)}


@mcp.tool()
def nf_get_items(
    run_id: str,
    stage: str = "filtered",
    max_items: int = 50,
) -> dict:
    """
    Get ContentItems from a specific run stage.

    Args:
        run_id: run identifier (from nf_list_runs)
        stage: "raw" | "scored" | "filtered"
        max_items: max items to return
    """
    storage = _storage()
    items = storage.load_items(run_id, stage=stage)
    return {
        "run_id": run_id,
        "stage": stage,
        "count": len(items),
        "items": [i.model_dump(mode="json") for i in items[:max_items]],
    }


@mcp.tool()
def nf_get_stats(run_id: str) -> dict:
    """Get stats for a pipeline run."""
    storage = _storage()
    meta = storage.load_meta(run_id)
    return {"run_id": run_id, **meta}


# ── Config tools ──────────────────────────────────────────────────────────────


@mcp.tool()
def nf_list_workflows() -> dict:
    """List available workflow YAML files."""
    workflows = []
    for p in sorted(_WORKFLOW_DIR.glob("*.yaml")):
        import yaml
        wf = yaml.safe_load(p.read_text())
        workflows.append({
            "name": p.stem,
            "description": wf.get("description", ""),
            "collectors": [c["type"] for c in wf.get("collectors", [])],
        })
    return {"workflows": workflows}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _resolve_workflow(name_or_path: str) -> Path:
    p = Path(name_or_path)
    if p.exists():
        return p
    # try config/workflows/<name>.yaml
    candidate = _WORKFLOW_DIR / f"{name_or_path}.yaml"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"Workflow '{name_or_path}' not found. "
        f"Available: {[p.stem for p in _WORKFLOW_DIR.glob('*.yaml')]}"
    )


if __name__ == "__main__":
    mcp.run()
