"""NewsFlow — Phase 2: Pipeline Engine (engine.py)

Loads a YAML workflow definition and executes:
  collectors → dedup → score → filter → (generators) → (publishers)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml

from newsflow.ai.client import AIClient
from newsflow.collectors.registry import get_collector
from newsflow.models.content import ContentItem
from newsflow.processors.filter import Deduplicator, ScoreFilter
from newsflow.processors.scorer import Scorer
from newsflow.storage.local import LocalStorage

logger = logging.getLogger(__name__)


class PipelineEngine:
    def __init__(
        self,
        workflow_path: str | Path,
        data_dir: str = "./data",
    ) -> None:
        self.workflow_path = Path(workflow_path)
        self.workflow = self._load_workflow(self.workflow_path)
        self.storage = LocalStorage(data_dir)
        self.ai = AIClient()

    # ── public ────────────────────────────────────────────────────────────────

    async def run(
        self,
        *,
        hours: int | None = None,
        dry_run: bool = False,
        sources: list[str] | None = None,
    ) -> dict:
        """
        Execute the full pipeline.
        Returns a summary dict with run_id and stats.
        """
        run_id = self.storage.new_run_id()
        wf = self.workflow
        _hours = hours or wf.get("hours", 24)

        logger.info("▶ Run %s | workflow: %s | hours: %d", run_id, wf.get("name"), _hours)

        # ── 1. Collect ────────────────────────────────────────────────────────
        raw_items = await self._collect(wf, _hours, sources)
        self.storage.save_items(run_id, raw_items, stage="raw")
        logger.info("  Collected %d items", len(raw_items))

        # ── 2. Dedup ──────────────────────────────────────────────────────────
        dedup = Deduplicator()
        deduped = dedup.dedup(raw_items)
        logger.info("  After dedup: %d items", len(deduped))

        # ── 3. Score ──────────────────────────────────────────────────────────
        filter_cfg: dict = wf.get("filter", {})
        scorer = Scorer(self.ai)
        scored = await scorer.score(deduped)
        self.storage.save_items(run_id, scored, stage="scored")

        # ── 4. Filter ─────────────────────────────────────────────────────────
        sf = ScoreFilter(
            threshold=filter_cfg.get("threshold", 7.0),
            max_items=filter_cfg.get("max_items", 20),
        )
        filtered = sf.filter(scored)
        self.storage.save_items(run_id, filtered, stage="filtered")
        logger.info("  Filtered to %d items (threshold=%.1f)", len(filtered), sf.threshold)

        # ── 5. Meta ───────────────────────────────────────────────────────────
        meta = {
            "workflow": wf.get("name", self.workflow_path.stem),
            "hours": _hours,
            "dry_run": dry_run,
            "stats": {
                "collected": len(raw_items),
                "deduped": len(deduped),
                "filtered": len(filtered),
                "token_used": self.ai.total_tokens,
            },
        }
        self.storage.save_meta(run_id, meta)
        logger.info("  Done. tokens used: %d", self.ai.total_tokens)

        return {"run_id": run_id, **meta}

    # ── private ───────────────────────────────────────────────────────────────

    async def _collect(
        self,
        wf: dict,
        hours: int,
        source_filter: list[str] | None,
    ) -> list[ContentItem]:
        collector_cfgs: list[dict] = wf.get("collectors", [])
        all_items: list[ContentItem] = []

        for cfg in collector_cfgs:
            ctype = cfg.get("type", "")
            if source_filter and ctype not in source_filter:
                continue
            limit = cfg.get("limit", 50)
            try:
                collector = get_collector(ctype, config=cfg.get("config", {}))
                items = await collector.collect(hours=hours, limit=limit)
                all_items.extend(items)
                logger.debug("  [%s] fetched %d", ctype, len(items))
            except Exception as exc:
                logger.warning("  [%s] collection failed: %s", ctype, exc)

        return all_items

    @staticmethod
    def _load_workflow(path: Path) -> dict:
        if not path.exists():
            raise FileNotFoundError(f"Workflow not found: {path}")
        return yaml.safe_load(path.read_text())
