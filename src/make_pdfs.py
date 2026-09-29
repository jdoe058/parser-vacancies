import csv
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import CSS, HTML

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "vacancies.csv"
CONFIG_PATH = BASE_DIR / "config" / "pdf.yaml"
TEMPLATES_DIR = BASE_DIR / "templates"
OUT_DIR = BASE_DIR / "output"


# ---------- загрузка ----------

def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_rows() -> list[dict[str, Any]]:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f)
                if any(v.strip() for v in r.values())]


# ---------- классификация ----------

def row_matches(row: dict[str, Any], include: dict[str, Any]) -> bool:
    """Проверяет, попадает ли вакансия в документ по правилам из config."""
    spec = (row.get("speciality") or "").strip().lower()
    title = (row.get("title") or "").strip()

    specs = [s.lower() for s in (include.get("specialities") or [])]
    if specs and spec in specs:
        return True

    for pattern in (include.get("title_patterns") or []):
        try:
            if re.search(pattern, title, re.IGNORECASE):
                return True
        except re.error:
            # не падаем из-за кривого регекса в конфиге — просто игнорируем его
            continue

    return False

# ---------- подготовка данных для шаблона ----------

def support_text(row: dict[str, Any], flags: list[dict[str, str]]) -> str:
    out = [f["label"] for f in flags
           if str(row.get(f["key"], "0")).strip() in ("1", "true", "True")]
    return ", ".join(out) if out else "—"


def build_cells(row: dict[str, Any], columns: list[dict[str, Any]],
                flags: list[dict[str, str]]) -> list[dict[str, str]]:
    cells: list[dict[str, str]] = []
    for col in columns:
        key = col["key"]
        if key == "n":
            cells.append({"cls": "n", "value": str(row.get("_n", ""))})
        elif key == "title":
            cells.append({"cls": "title", "value": row.get("title") or "—"})
        elif key == "organization":
            cells.append({"cls": "org", "value": row.get("organization") or "—"})
        elif key == "qty":
            v = (row.get("qty") or "—").strip() or "—"
            cells.append({"cls": "qty", "value": v})
        elif key == "support":
            cells.append({"cls": "support", "value": support_text(row, flags)})
        elif key == "area":
            cells.append({"cls": "area", "value": row.get("area") or "—"})
        elif key == "speciality":
            cells.append({"cls": "spec", "value": row.get("speciality") or "—"})
        elif key == "work_mode":
            cells.append({"cls": "mode", "value": row.get("work_mode") or "—"})
        else:
            cells.append({"cls": key, "value": row.get(key) or "—"})
    return cells


def group_by_area(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_area: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_area[(r.get("area") or "—").strip()].append(r)

    groups: list[dict[str, Any]] = []
    n = 0
    for area in sorted(by_area.keys()):
        items = sorted(
            by_area[area],
            key=lambda x: ((x.get("organization") or "").lower(),
                           (x.get("title") or "").lower()),
        )
        prepared = []
        for i, r in enumerate(items):
            n += 1
            r["_n"] = n
            r["_alt"] = (i % 2 == 1)
            prepared.append(r)
        groups.append({"area": area, "rows": prepared})
    return groups


# ---------- рендер ----------

def render_pdf(rows: list[dict[str, Any]], doc_key: str,
               config: dict[str, Any]) -> Path:
    common = config["common"]
    doc = config[doc_key]

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    groups = group_by_area(rows)
    for group in groups:
        for r in group["rows"]:
            r["cells"] = build_cells(r, doc["columns"], common["support_flags"])

    html_template = env.get_template(doc["template"])
    html_text = html_template.render(
        title=doc["title"],
        subtitle=doc["subtitle"],
        description=doc["description"],
        columns=doc["columns"],
        groups=groups,
        total=len(rows),
        date=datetime.now().strftime("%d.%m.%Y"),
        config=config,
    )

    css_template = env.get_template("style.css.jinja")
    css_text = css_template.render(config=config)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / doc["output"]

    HTML(string=html_text, base_url=str(TEMPLATES_DIR)).write_pdf(
        str(out_path),
        stylesheets=[CSS(string=css_text)],
    )
    return out_path


# ---------- main ----------

def main() -> None:
    config = load_config()
    rows = read_rows()

    for key, doc in config.items():
        if key == "common":
            continue

        include = doc.get("include", {})
        matched = [r for r in rows if row_matches(r, include)]

        if not matched:
            print(f"[{key}] нет вакансий по правилам из config — пропускаю")
            continue

        out = render_pdf(matched, key, config)
        print(f"[{key}] {len(matched)} вакансий -> {out}")


if __name__ == "__main__":
    main()