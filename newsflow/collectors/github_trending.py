"""NewsFlow — Phase 1: Collectors (github_trending.py)

Scrapes GitHub Trending page (no API key required).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from newsflow.collectors.base import BaseCollector
from newsflow.models.content import ContentItem, SourceType

TRENDING_URL = "https://github.com/trending"


class GitHubTrendingCollector(BaseCollector):
    source_type = SourceType.GITHUB_TRENDING

    async def collect(self, *, hours: int = 24, limit: int = 30) -> list[ContentItem]:
        """
        GitHub Trending doesn't expose timestamps, so `hours` is ignored.
        Returns up to `limit` trending repos.
        """
        language = self.config.get("language", "")
        since = self.config.get("since", "daily")  # daily / weekly / monthly
        url = TRENDING_URL
        params: dict[str, str] = {"since": since}
        if language:
            url = f"{TRENDING_URL}/{language}"

        async with self.make_client() as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        items: list[ContentItem] = []
        now = self.now_utc()

        for article in soup.select("article.Box-row")[:limit]:
            # repo full name
            h2 = article.find("h2")
            if not h2:
                continue
            repo_path = re.sub(r"\s+", "", h2.get_text(separator="/")).strip("/")

            # description
            desc_tag = article.find("p")
            description = desc_tag.get_text(strip=True) if desc_tag else ""

            # stars today
            stars_spans = article.select("span.d-inline-block.float-sm-right")
            stars_today = ""
            if stars_spans:
                stars_today = stars_spans[0].get_text(strip=True)

            # total stars / forks
            star_tag = article.find("a", href=re.compile(r"/stargazers$"))
            total_stars = star_tag.get_text(strip=True) if star_tag else ""

            # language
            lang_tag = article.find("span", itemprop="programmingLanguage")
            lang = lang_tag.get_text(strip=True) if lang_tag else ""

            repo_url = f"https://github.com/{repo_path}"
            safe_id = repo_path.replace("/", "_").lower()

            items.append(
                ContentItem(
                    id=f"github_trending:repo:{safe_id}",
                    source_type=SourceType.GITHUB_TRENDING,
                    title=repo_path,
                    url=repo_url,
                    content=description,
                    published_at=now,
                    fetched_at=now,
                    metadata={
                        "stars_today": stars_today,
                        "total_stars": total_stars,
                        "language": lang,
                        "since": since,
                    },
                )
            )

        return items
