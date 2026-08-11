# Colin Masson — ARC Advisory Group Article Index

**Author:** Colin Masson, Director of Research for Industrial AI, ARC Advisory Group
**Compiled:** 11 August 2026
**Note:** The LinkedIn posts are republications. The original, canonical versions live on ARCweb.com (open access, no login required) — these are the download sources.

---

## A. "Draining the Agentic Swamp" Blog Series

| # | Title | Published | Link |
|---|-------|-----------|------|
| 1 | Draining the Agentic Swamp: Moving from Passive Containment to Active Architectural Remediation | Jul 2026 | https://www.arcweb.com/blog/draining-agentic-swamp-moving-passive-containment-active-architectural-remediation |
| 2 | The Open Architecture Contract: How MCP and i3X Act as the Drainage Pumps of the Autonomous Plant | 5 Aug 2026 | https://www.arcweb.com/blog/open-architecture-contract-how-mcp-i3x-act-drainage-pumps-autonomous-plant |
| 3 | The Silicon vs. Carbon Ledger: The Unforgiving Mathematics of the Agentic Labor Trade-Off | 7 Aug 2026 | https://www.arcweb.com/blog/silicon-vs-carbon-ledger-unforgiving-mathematics-agentic-labor-trade |
| 4 | The Moral, Ethical, and Safety Boundaries of the Silicon Workforce: Who Arbitrates the Algorithm? | **Announced — not yet published** | Watch: https://www.arcweb.com/blog/industrial-ai-viewpoints |

---

## B. "Industrial AI (R)Evolution" Articles

Hub page: https://www.arcweb.com/industry-best-practices/industrial-ai-revolution

| # | Title | Link |
|---|-------|------|
| 1 | Navigating the AI Wars | https://www.arcweb.com/blog/ai-wars-battlefronts-breakthroughs-new-era-industrial-ai-revolution |
| 2 | Industrial Robot Wars: Navigating New Battlefronts of Physical Intelligence | https://www.arcweb.com/blog/industrial-robot-wars-navigating-new-battlefronts-physical-intelligence |
| 3 | Closing the Digital Divide by Embracing Industrial AI | https://www.arcweb.com/industry-best-practices/widening-digital-divide-how-leaders-embracing-industrial-ai |
| 4 | Laying the Foundations: ARC's Industrial Data Fabric Reports | https://www.arcweb.com/blog/laying-foundations-industrial-ai-revolution-announcing-arcs-industrial-data-fabric-reports |
| 5 | The Voyage Continues: Charting the New World of Physical Intelligence | https://www.arcweb.com/blog/voyage-continues-charting-new-world-physical-intelligence |
| 6 | The Context Engineering Continuum: Equipping the Industrial Data Fabric for the Cyber-Physical Era (CPIA) | https://www.arcweb.com/blog/context-engineering-continuum-equipping-industrial-data-fabric-cyber-physical-era |
| 7 | How ARC's Taxonomy & Market Maps Drive Rapid Time-to-Industrial-AI Value (3-Axis Taxonomy) | https://www.arcweb.com/blog/how-arcs-taxonomy-market-maps-drive-rapid-time-industrial-ai-value |

---

## How to download them all in one go

1. Install Python 3 (if not already installed) and run: `pip install requests`
2. From the repository root, run: `python download_masson_articles.py`
3. It fills this folder with two subfolders (`series/` + `references/`) and saves each article as an offline-readable HTML file.
4. For PDF copies: open any saved HTML file in your browser and use Print → Save as PDF.

When Blog 4 goes live, uncomment its line in the script and re-run — it only downloads what's missing.

> **Note:** Claude Code's remote environment could not run the download itself — its network egress policy only allows package registries and GitHub, and blocks arcweb.com (and archive.org mirrors). Run the script on a machine with normal internet access.
