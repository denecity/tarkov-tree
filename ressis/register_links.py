from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

# Default locations and selectors for the saved wiki page.
DEFAULT_HTML = "Quests - The Official Escape from Tarkov Wiki.htm"
DEFAULT_OUTPUT = "quest_links.json"
DEFAULT_BASE_URL = "https://escapefromtarkov.fandom.com"
NAVBOX_SELECTOR = "table.navbox.va-navbox-border.va-navbox-bottom"


def extract_quest_links(html_path: Path, base_url: str = DEFAULT_BASE_URL) -> List[Dict[str, str]]:
    """
    Parse the quest navbox and return quest links with their owning trader.
    """
    html_text = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html_text, "html.parser")

    navbox = soup.select_one(NAVBOX_SELECTOR)
    if navbox is None:
        raise RuntimeError(f"Navbox ({NAVBOX_SELECTOR}) not found in {html_path}")

    quests: List[Dict[str, str]] = []
    seen_hrefs = set()

    for row in navbox.select("tr"):
        trader_cell = row.select_one("td.va-navbox-group")
        trader = trader_cell.get_text(strip=True) if trader_cell else None

        for quests_cell in row.select("td.va-navbox-cell"):
            for link in quests_cell.find_all("a", href=True):
                href = link["href"]
                if "/wiki/" not in href:
                    continue

                full_url = urljoin(base_url, href)
                if full_url in seen_hrefs:
                    continue

                seen_hrefs.add(full_url)
                quests.append(
                    {
                        "title": link.get_text(" ", strip=True),
                        "href": full_url,
                        "trader": trader,
                    }
                )

    return quests


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract quest links from the saved Tarkov wiki page.")
    parser.add_argument("--html", default=DEFAULT_HTML, type=Path, help="Path to the saved HTML file.")
    parser.add_argument("--out", default=DEFAULT_OUTPUT, type=Path, help="Where to write the quest link JSON.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Base URL used to resolve relative wiki links.",
    )
    args = parser.parse_args()

    quests = extract_quest_links(args.html, base_url=args.base_url)
    args.out.write_text(json.dumps(quests, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(quests)} quest links to {args.out}")


if __name__ == "__main__":
    main()
