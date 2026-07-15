"""NewsFlow — Phase 2: Storage (local.py)

JSON file storage. Each run gets a directory under data/runs/{run_id}/.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from newsflow.models.content import ContentItem
from newsflow.models.output import ArticleOutput


class LocalStorage:
    def __init__(self, data_dir: str = "./data") -> None:
        self.root = Path(data_dir) / "runs"
        self.root.mkdir(parents=True, exist_ok=True)

    # ── run helpers ───────────────────────────────────────────────────────────

    def new_run_id(self) -> str:
        return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    def run_dir(self, run_id: str) -> Path:
        d = self.root / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ── write ─────────────────────────────────────────────────────────────────

    def save_items(
        self, run_id: str, items: list[ContentItem], stage: str = "raw"
    ) -> Path:
        path = self.run_dir(run_id) / f"{stage}.json"
        data = [item.model_dump(mode="json") for item in items]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        return path

    def save_articles(self, run_id: str, articles: list[ArticleOutput]) -> Path:
        path = self.run_dir(run_id) / "articles.json"
        data = [a.model_dump(mode="json") for a in articles]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        return path

    def save_meta(self, run_id: str, meta: dict) -> Path:
        path = self.run_dir(run_id) / "meta.json"
        path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        return path

    # ── read ──────────────────────────────────────────────────────────────────

    def load_items(self, run_id: str, stage: str = "raw") -> list[ContentItem]:
        path = self.run_dir(run_id) / f"{stage}.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text())
        return [ContentItem(**d) for d in data]

    def load_articles(self, run_id: str) -> list[ArticleOutput]:
        path = self.run_dir(run_id) / "articles.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text())
        return [ArticleOutput(**d) for d in data]

    def load_meta(self, run_id: str) -> dict:
        path = self.run_dir(run_id) / "meta.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text())

    # ── list ──────────────────────────────────────────────────────────────────

    def list_runs(self, limit: int = 10) -> list[dict]:
        dirs = sorted(self.root.iterdir(), reverse=True)[:limit]
        result = []
        for d in dirs:
            if d.is_dir():
                meta = self.load_meta(d.name)
                result.append({"run_id": d.name, **meta})
        return result
