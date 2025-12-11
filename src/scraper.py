from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

USER_AGENT = "quest-scraper/1.0 (+https://github.com/)"  # polite UA
DEFAULT_INPUT = "src/quest_links.json"
DEFAULT_OUTPUT = "src/quests.csv"


@dataclass
class Quest:
    name: str
    location: Optional[str]
    given_by: Optional[str]
    dialogue: List[str]
    requirements: List[str]
    objectives: List[str]
    rewards: List[str]
    previous: List[str]
    leads_to: List[str]

    def as_row(self) -> dict:
        data = asdict(self)
        # Flatten list-like fields into pipe-delimited strings for CSV usability.
        for key in ["dialogue", "requirements", "objectives", "rewards", "previous", "leads_to"]:
            data[key] = " | ".join(data[key]) if data[key] else ""
        return data


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return resp.text


def get_infobox(soup: BeautifulSoup):
    return soup.find("table", class_="va-infobox")


def extract_infobox_value(soup: BeautifulSoup, label: str) -> Optional[str]:
    infobox = get_infobox(soup)
    if not infobox:
        return None
    for cell in infobox.find_all("td", class_="va-infobox-label"):
        if cell.get_text(" ", strip=True).lower().startswith(label.lower()):
            content = cell.find_next("td", class_="va-infobox-content")
            if content:
                return content.get_text(" ", strip=True)
    return None


def extract_related(soup: BeautifulSoup):
    """
    Extract 'Previous' and 'Leads to' lists from the infobox related section.
    """
    previous, leads_to = [], []
    infobox = get_infobox(soup)
    if not infobox:
        return previous, leads_to

    for cell in infobox.select("td.va-infobox-content"):
        text = cell.get_text(" ", strip=True).lower()
        links = [a.get_text(" ", strip=True) for a in cell.select("a[href]")]
        if text.startswith("previous:"):
            previous.extend(links)
        elif text.startswith("leads to:"):
            leads_to.extend(links)
    return previous, leads_to


def extract_section_lines(soup: BeautifulSoup, section_id: str) -> List[str]:
    """
    Return a list of text lines that belong to a section (Objectives, Dialogue, Rewards, etc.).
    Stops when the next heading of the same level begins.
    """
    headline = soup.find(id=section_id)
    if not headline:
        return []

    heading = headline.find_parent(["h2", "h3", "h4"])
    if not heading:
        return []

    lines: List[str] = []
    for sib in heading.next_siblings:
        if getattr(sib, "name", None) in ["h2", "h3", "h4"]:
            break
        if getattr(sib, "name", None) == "ul":
            for li in sib.find_all("li", recursive=False):
                text = li.get_text(" ", strip=True)
                if text:
                    lines.append(text)
        elif getattr(sib, "name", None) == "p":
            text = sib.get_text(" ", strip=True)
            if text:
                lines.append(text)
    return lines


def scrape_quest(url: str) -> Quest:
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    name = soup.find("h1", id="firstHeading")
    quest_name = name.get_text(" ", strip=True) if name else url

    given_by = extract_infobox_value(soup, "Given by")
    location = extract_infobox_value(soup, "Location")
    previous, leads_to = extract_related(soup)
    dialogue = extract_section_lines(soup, "Dialogue")
    requirements = extract_section_lines(soup, "Requirements")
    objectives = extract_section_lines(soup, "Objectives")
    rewards = extract_section_lines(soup, "Rewards")

    return Quest(
        name=quest_name,
        location=location,
        given_by=given_by,
        dialogue=dialogue,
        requirements=requirements,
        objectives=objectives,
        rewards=rewards,
        previous=previous,
        leads_to=leads_to,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape quest details from Tarkov wiki pages.")
    parser.add_argument("--links", default=DEFAULT_INPUT, type=Path, help="Path to quest_links.json")
    parser.add_argument("--out", default=DEFAULT_OUTPUT, type=Path, help="Where to write the CSV")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of quests for quick testing")
    args = parser.parse_args()

    quest_links = json.loads(Path(args.links).read_text(encoding="utf-8"))
    if args.limit:
        quest_links = quest_links[: args.limit]

    rows = []
    for idx, q in enumerate(quest_links, start=1):
        print(f"[{idx}/{len(quest_links)}] Scraping {q['title']}...")
        quest = scrape_quest(q["href"])
        rows.append(quest.as_row())

    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False, encoding="utf-8")
    print(f"Wrote {len(df)} quests to {args.out}")


if __name__ == "__main__":
    main()
