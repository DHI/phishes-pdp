"""Generate an HTML overview report collecting all PNG plots from a result directory."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_3DSZ_PATTERN = re.compile(
    r"^(.+)_3dsz_crossrun_(\d{4}_\d{2}_\d{2}(?:_\d{2}_\d{2}_\d{2})?)\.png$"
)
_OVERLAND_PATTERN = re.compile(r"^(.+)_overland_.+\.png$")

_DIAG_SECTION_LABELS = {
    "volume_terms_by_variable": "Coupling Volume Terms",
    "closure_terms_by_variable": "Volume Closure Errors",
    "matrix_percolation_effective_state": "UZ Water Content State",
}

_3DSZ_ITEM_LABELS = {
    "groundwater_flow_in_x_direction": "Groundwater Flow — X direction",
    "groundwater_flow_in_y_direction": "Groundwater Flow — Y direction",
    "groundwater_flux_in_z_direction": "Groundwater Flux — Z direction (vertical)",
    "sz_exchange_flow_with_river": "SZ ↔ River Exchange Flow",
    "sz_drainage_flow_from_point": "SZ Drainage Flow (point sources)",
    "external_sources_to_sz_for_openmi": "External Sources to SZ (OpenMI)",
}


def _slug_to_label(slug: str) -> str:
    label = _3DSZ_ITEM_LABELS.get(slug)
    if label:
        return label
    return slug.replace("_", " ").title()


def _date_from_slug(slug: str) -> str:
    parts = slug.split("_")
    if len(parts) >= 3:
        return f"{parts[0]}-{parts[1]}-{parts[2]}"
    return slug


def _rel(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _img_tag(rel_path: str, caption: str = "", width: str = "100%") -> str:
    title = caption.replace('"', "&quot;")
    figcaption = (
        f'<figcaption style="font-size:0.8em;color:#555;margin-top:0.3em">{caption}</figcaption>'
        if caption
        else ""
    )
    return (
        f'<figure style="margin:0">'
        f'<img src="{rel_path}" alt="{title}" title="{title}" style="max-width:{width};height:auto;border:1px solid #ddd;border-radius:3px">'
        f"{figcaption}"
        f"</figure>"
    )


def _section_id(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def generate_report(result_dir: Path, output_path: Path | None = None) -> Path:
    if output_path is None:
        output_path = result_dir / "report.html"

    all_pngs = sorted(result_dir.rglob("*.png"))

    # Collect diagnostics from *_plots subdirs
    diag_sections: list[tuple[str, str, list[Path]]] = []
    diag_dirs = sorted({p.parent for p in all_pngs if p.parent != result_dir})
    for diag_dir in diag_dirs:
        dir_pngs = sorted(p for p in all_pngs if p.parent == diag_dir)
        for png in dir_pngs:
            stem = png.stem
            label = _DIAG_SECTION_LABELS.get(stem, _slug_to_label(stem))
            diag_sections.append((label, _section_id(label), [png]))

    # Collect 3DSZ crossrun pngs from root, group by item
    by_item: dict[str, list[tuple[str, Path]]] = {}
    overland_pngs: list[Path] = []
    uncategorised: list[Path] = []

    for png in all_pngs:
        if png.parent != result_dir:
            continue
        m3 = _3DSZ_PATTERN.match(png.name)
        if m3:
            item_slug, date_slug = m3.group(1), m3.group(2)
            by_item.setdefault(item_slug, []).append((_date_from_slug(date_slug), png))
            continue
        mo = _OVERLAND_PATTERN.match(png.name)
        if mo:
            overland_pngs.append(png)
            continue
        uncategorised.append(png)

    # Sort each item's timesteps
    for slug in by_item:
        by_item[slug].sort(key=lambda x: x[0])

    # Build sections HTML + nav entries
    sections_html: list[str] = []
    nav_entries: list[str] = []

    def _add_section(section_id: str, title: str, body_html: str) -> None:
        sections_html.append(
            f'<section id="{section_id}"><h2>{title}</h2>{body_html}</section>'
        )
        nav_entries.append(f'<a href="#{section_id}">{title}</a>')

    # Diagnostics
    if diag_sections:
        diag_body = ""
        for label, sid, pngs in diag_sections:
            diag_body += f'<h3 id="{sid}">{label}</h3>'
            for png in pngs:
                diag_body += _img_tag(_rel(png, result_dir), width="860px")
        _add_section("diagnostics", "Coupling Diagnostics", diag_body)

    # 3DSZ per item
    for item_slug, timesteps in sorted(by_item.items()):
        label = _slug_to_label(item_slug)
        sid = _section_id(label)
        body = (
            '<div style="display:flex;flex-wrap:wrap;gap:0.8em;align-items:flex-start">'
        )
        for date_label, png in timesteps:
            body += (
                '<div style="flex:1 1 280px;min-width:220px;max-width:400px">'
                + _img_tag(_rel(png, result_dir), caption=date_label)
                + "</div>"
            )
        body += "</div>"
        _add_section(sid, label, body)

    # Overland
    if overland_pngs:
        body = ""
        for png in sorted(overland_pngs):
            body += _img_tag(
                _rel(png, result_dir), caption=png.stem.replace("_", " "), width="860px"
            )
        _add_section("overland", "Overland Flow", body)

    if uncategorised:
        body = '<div style="display:flex;flex-wrap:wrap;gap:0.8em">'
        for png in uncategorised:
            body += (
                '<div style="flex:1 1 300px">'
                + _img_tag(_rel(png, result_dir), caption=png.stem)
                + "</div>"
            )
        body += "</div>"
        _add_section("other", "Other", body)

    nav_html = "\n".join(nav_entries)
    body_html = "\n".join(sections_html)
    run_label = result_dir.name
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Run Report — {run_label}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: system-ui, sans-serif; margin: 0; display: flex; background: #fafafa; color: #222; }}
  nav {{ width: 230px; min-width: 180px; padding: 1.2em 1em; position: sticky; top: 0; height: 100vh; overflow-y: auto; background: #f0f0f0; border-right: 1px solid #ddd; font-size: 0.82em; }}
  nav strong {{ display: block; margin-bottom: 0.8em; font-size: 1em; }}
  nav a {{ display: block; padding: 0.2em 0; text-decoration: none; color: #1a5276; }}
  nav a:hover {{ text-decoration: underline; }}
  main {{ flex: 1; padding: 2em 2.5em; max-width: 1400px; }}
  h1 {{ font-size: 1.4em; margin-bottom: 0.2em; }}
  .meta {{ color: #666; font-size: 0.85em; margin-bottom: 2em; }}
  section {{ margin-bottom: 3em; }}
  h2 {{ font-size: 1.15em; border-bottom: 2px solid #1a5276; padding-bottom: 0.3em; color: #1a5276; }}
  h3 {{ font-size: 0.95em; color: #444; margin-top: 1.2em; }}
  figcaption {{ font-size: 0.78em; color: #555; margin-top: 0.25em; }}
</style>
</head>
<body>
<nav>
  <strong>Contents</strong>
  {nav_html}
</nav>
<main>
  <h1>Run Report</h1>
  <p class="meta">{run_label}<br>Generated: {generated_at}</p>
  {body_html}
</main>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate HTML report from result directory PNGs."
    )
    parser.add_argument(
        "--result-dir", required=True, help="Path to the result files directory."
    )
    parser.add_argument(
        "--output", help="Output HTML path. Defaults to <result-dir>/report.html."
    )
    args = parser.parse_args()

    result_dir = Path(args.result_dir).expanduser().resolve()
    if not result_dir.is_dir():
        print(f"Error: {result_dir} is not a directory.", file=sys.stderr)
        return 1

    output_path = Path(args.output).resolve() if args.output else None
    written = generate_report(result_dir, output_path)
    print(f"Report written to: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
