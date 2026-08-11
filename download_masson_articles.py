#!/usr/bin/env python3
"""Download Colin Masson's ARC Advisory Group articles for offline reading.

Companion script for the "Colin Masson — ARC Advisory Group Article Index"
(see Masson_ARC_Articles/README.md). Downloads the canonical, open-access
versions from ARCweb.com and saves each one as an offline-readable HTML file.

Usage:
    pip install requests
    python download_masson_articles.py

Output layout:
    Masson_ARC_Articles/
        series/       "Draining the Agentic Swamp" blog series
        references/   "Industrial AI (R)Evolution" articles

Re-running is safe: files that already exist are skipped, so when a new
article goes live you can uncomment its line below and run the script again —
it only downloads what's missing.
"""

import sys
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent / "Masson_ARC_Articles"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

RETRIES = 3
TIMEOUT = 60  # seconds per request

# (filename, url) — filenames are numbered to match the index tables.
SERIES = [
    (
        "01_draining-the-agentic-swamp-passive-containment-to-active-architectural-remediation.html",
        "https://www.arcweb.com/blog/draining-agentic-swamp-moving-passive-containment-active-architectural-remediation",
    ),
    (
        "02_the-open-architecture-contract-mcp-and-i3x-drainage-pumps-of-the-autonomous-plant.html",
        "https://www.arcweb.com/blog/open-architecture-contract-how-mcp-i3x-act-drainage-pumps-autonomous-plant",
    ),
    (
        "03_the-silicon-vs-carbon-ledger-unforgiving-mathematics-of-the-agentic-labor-trade-off.html",
        "https://www.arcweb.com/blog/silicon-vs-carbon-ledger-unforgiving-mathematics-agentic-labor-trade",
    ),
    # Blog 4 — announced but not yet published. Uncomment when it goes live
    # (watch https://www.arcweb.com/blog/industrial-ai-viewpoints) and re-run:
    # (
    #     "04_moral-ethical-and-safety-boundaries-of-the-silicon-workforce-who-arbitrates-the-algorithm.html",
    #     "https://www.arcweb.com/blog/<final-url-when-published>",
    # ),
]

REFERENCES = [
    (
        "01_navigating-the-ai-wars.html",
        "https://www.arcweb.com/blog/ai-wars-battlefronts-breakthroughs-new-era-industrial-ai-revolution",
    ),
    (
        "02_industrial-robot-wars-navigating-new-battlefronts-of-physical-intelligence.html",
        "https://www.arcweb.com/blog/industrial-robot-wars-navigating-new-battlefronts-physical-intelligence",
    ),
    (
        "03_closing-the-digital-divide-by-embracing-industrial-ai.html",
        "https://www.arcweb.com/industry-best-practices/widening-digital-divide-how-leaders-embracing-industrial-ai",
    ),
    (
        "04_laying-the-foundations-arcs-industrial-data-fabric-reports.html",
        "https://www.arcweb.com/blog/laying-foundations-industrial-ai-revolution-announcing-arcs-industrial-data-fabric-reports",
    ),
    (
        "05_the-voyage-continues-charting-the-new-world-of-physical-intelligence.html",
        "https://www.arcweb.com/blog/voyage-continues-charting-new-world-physical-intelligence",
    ),
    (
        "06_the-context-engineering-continuum-industrial-data-fabric-for-the-cyber-physical-era.html",
        "https://www.arcweb.com/blog/context-engineering-continuum-equipping-industrial-data-fabric-cyber-physical-era",
    ),
    (
        "07_how-arcs-taxonomy-and-market-maps-drive-rapid-time-to-industrial-ai-value.html",
        "https://www.arcweb.com/blog/how-arcs-taxonomy-market-maps-drive-rapid-time-industrial-ai-value",
    ),
]


def make_offline_readable(html: str) -> str:
    """Inject a <base> tag so relative links, CSS, and images still resolve
    against arcweb.com when the saved file is opened from disk."""
    lowered = html.lower()
    idx = lowered.find("<head")
    if idx == -1:
        return html
    end = html.find(">", idx)
    if end == -1:
        return html
    return html[: end + 1] + '\n<base href="https://www.arcweb.com/">' + html[end + 1 :]


def download(url: str, dest: Path) -> str:
    if dest.exists():
        return "skipped"
    last_error = None
    for attempt in range(1, RETRIES + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            dest.write_text(make_offline_readable(response.text), encoding="utf-8")
            return "downloaded"
        except requests.RequestException as exc:
            last_error = exc
            if attempt < RETRIES:
                time.sleep(2**attempt)
    print(f"  FAILED after {RETRIES} attempts: {last_error}", file=sys.stderr)
    return "failed"


def main() -> int:
    counts = {"downloaded": 0, "skipped": 0, "failed": 0}
    for subfolder, articles in (("series", SERIES), ("references", REFERENCES)):
        folder = BASE_DIR / subfolder
        folder.mkdir(parents=True, exist_ok=True)
        for filename, url in articles:
            dest = folder / filename
            print(f"{subfolder}/{filename}")
            result = download(url, dest)
            counts[result] += 1
            print(f"  {result}")
    print(
        f"\nDone: {counts['downloaded']} downloaded, "
        f"{counts['skipped']} already present, {counts['failed']} failed."
    )
    print(f"Articles are in: {BASE_DIR}")
    print("For PDF copies: open a saved HTML file in your browser, then Print -> Save as PDF.")
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
