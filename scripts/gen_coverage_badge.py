#!/usr/bin/env python3
"""
Generate a coverage badge SVG from coverage.xml (Cobertura).

Usage:
  python scripts/gen_coverage_badge.py coverage.xml badges/coverage.svg
"""
import os
import sys
import xml.etree.ElementTree as ET


def read_coverage_percent(path: str) -> int:
    tree = ET.parse(path)
    root = tree.getroot()
    # Cobertura root may be <coverage> with line-rate attribute
    rate = root.attrib.get("line-rate")
    if rate is not None:
        try:
            return int(round(float(rate) * 100))
        except ValueError:
            pass
    # Fallback: sum package/class metrics
    total_lines = 0
    covered_lines = 0
    for cls in root.findall(".//class"):
        lines = cls.find("lines")
        if lines is None:
            continue
        for line in lines.findall("line"):
            total_lines += 1
            hits = int(line.attrib.get("hits", "0"))
            if hits > 0:
                covered_lines += 1
    if total_lines == 0:
        return 0
    return int(round(covered_lines * 100.0 / total_lines))


def color_for(pct: int) -> str:
    if pct >= 95:
        return "#4c1"  # brightgreen
    if pct >= 90:
        return "#97CA00"  # green
    if pct >= 80:
        return "#a4a61d"  # yellowgreen
    if pct >= 70:
        return "#dfb317"  # yellow
    if pct >= 50:
        return "#fe7d37"  # orange
    return "#e05d44"  # red


def make_svg(pct: int) -> str:
    label = "coverage"
    value = f"{pct}%"
    # Simple badge layout
    # Dimensions
    label_w = 74
    value_w = 52
    total_w = label_w + value_w
    color = color_for(pct)
    return f"""
<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{total_w}\" height=\"20\">
  <linearGradient id=\"b\" x2=\"0\" y2=\"100%\">
    <stop offset=\"0\" stop-color=\"#bbb\" stop-opacity=\".1\"/>
    <stop offset=\"1\" stop-opacity=\".1\"/>
  </linearGradient>
  <mask id=\"a\">
    <rect width=\"{total_w}\" height=\"20\" rx=\"3\" fill=\"#fff\"/>
  </mask>
  <g mask=\"url(#a)\">
    <rect width=\"{label_w}\" height=\"20\" fill=\"#555\"/>
    <rect x=\"{label_w}\" width=\"{value_w}\" height=\"20\" fill=\"{color}\"/>
    <rect width=\"{total_w}\" height=\"20\" fill=\"url(#b)\"/>
  </g>
  <g fill=\"#fff\" text-anchor=\"middle\" font-family=\"Verdana,DejaVu Sans,sans-serif\" font-size=\"11\">
    <text x=\"{label_w/2}\" y=\"15\">{label}</text>
    <text x=\"{label_w + value_w/2}\" y=\"15\">{value}</text>
  </g>
</svg>
"""


def main(argv):
    if len(argv) != 3:
        print("Usage: python scripts/gen_coverage_badge.py coverage.xml badges/coverage.svg")
        return 2
    src, dst = argv[1], argv[2]
    pct = read_coverage_percent(src)
    svg = make_svg(pct)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote {dst} with {pct}% coverage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
