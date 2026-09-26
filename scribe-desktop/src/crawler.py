"""arXiv crawler.

Respects https://arxiv.org/robots.txt for a generic user-agent:
    Allow: /catchup, /abs, /pdf, /list      Crawl-delay: 15      Disallow: /api, /search, ...

We use /catchup/<category>/<YYYY-MM-DD>?abs=True&page=N, which is arXiv's own
"catch up on one day" view. It returns that day's "New submissions" (plus
cross-lists/replacements, which we skip) with the full abstract inlined, so a
single day's papers cost one request instead of one listing + N abstract
fetches. Every request goes through `_get`, which enforces the crawl-delay.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from . import config

_last_request_at: float = 0.0


def _get(url: str, params: dict | None = None) -> requests.Response:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    wait = config.CRAWL_DELAY_SECONDS - elapsed
    if wait > 0:
        time.sleep(wait)
    resp = requests.get(
        url,
        params=params,
        headers={"User-Agent": config.USER_AGENT},
        timeout=config.REQUEST_TIMEOUT_SECONDS,
    )
    _last_request_at = time.monotonic()
    resp.raise_for_status()
    return resp


@dataclass
class Paper:
    arxiv_id: str
    title: str
    authors: str
    abstract: str
    comments: str
    subjects: str
    primary_subject: str
    category: str
    published_date: str
    abs_url: str
    pdf_url: str

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def _parse_new_submissions(html: str, category: str, date: str) -> list[Paper]:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h3", string=re.compile(r"New submissions"))
    papers: list[Paper] = []
    if heading is None:
        return papers

    dl = heading.find_next("dl", id="articles")
    if dl is None:
        return papers

    for dt in dl.find_all("dt", recursive=False):
        dd = dt.find_next_sibling("dd")
        if dd is None:
            continue

        abs_link = dt.find("a", title="Abstract")
        if abs_link is None:
            continue
        arxiv_id = abs_link.get_text(strip=True).replace("arXiv:", "").strip()

        title_div = dd.find("div", class_="list-title")
        title = title_div.get_text(" ", strip=True).replace("Title:", "").strip() if title_div else ""

        authors_div = dd.find("div", class_="list-authors")
        authors = ", ".join(a.get_text(strip=True) for a in authors_div.find_all("a")) if authors_div else ""

        comments_div = dd.find("div", class_="list-comments")
        comments = comments_div.get_text(" ", strip=True).replace("Comments:", "").strip() if comments_div else ""

        subjects_div = dd.find("div", class_="list-subjects")
        subjects = subjects_div.get_text(" ", strip=True).replace("Subjects:", "").strip() if subjects_div else ""
        primary_span = subjects_div.find("span", class_="primary-subject") if subjects_div else None
        primary_subject = primary_span.get_text(strip=True) if primary_span else subjects

        abstract_p = dd.find("p", class_="mathjax")
        abstract = abstract_p.get_text(" ", strip=True) if abstract_p else ""

        papers.append(
            Paper(
                arxiv_id=arxiv_id,
                title=title,
                authors=authors,
                abstract=abstract,
                comments=comments,
                subjects=subjects,
                primary_subject=primary_subject,
                category=category,
                published_date=date,
                abs_url=f"{config.ARXIV_BASE_URL}/abs/{arxiv_id}",
                pdf_url=f"{config.ARXIV_BASE_URL}/pdf/{arxiv_id}",
            )
        )
    return papers


def fetch_day(date: str, category: str = config.DEFAULT_CATEGORY, max_pages: int = 10) -> list[Paper]:
    """Fetch all 'new submission' papers for one category on one day (YYYY-MM-DD)."""
    all_papers: list[Paper] = []
    seen_ids: set[str] = set()
    for page in range(1, max_pages + 1):
        url = f"{config.ARXIV_BASE_URL}/catchup/{category}/{date}"
        resp = _get(url, params={"abs": "True", "page": page})
        page_papers = _parse_new_submissions(resp.text, category, date)
        new_on_page = [p for p in page_papers if p.arxiv_id not in seen_ids]
        if not new_on_page:
            break
        for p in new_on_page:
            seen_ids.add(p.arxiv_id)
        all_papers.extend(new_on_page)
        if len(page_papers) < 100:
            break
    return all_papers
