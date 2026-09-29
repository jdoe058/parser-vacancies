import csv
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)

CSV_PATH = Path("data/vacancies.csv")
OUT_DIR = Path("output")
OUT_DIR.mkdir(exist_ok=True)

AUTHOR = "Региональный кадровый центр Краснодарского края"


# ---------- шрифт с кириллицей ----------

def register_fonts() -> tuple[str, str]:
    candidates = [
        ("Arial", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("Times", "C:/Windows/Fonts/times.ttf", "C:/Windows/Fonts/timesbd.ttf"),
        ("Liberation",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        ("DejaVu",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for name, reg, bold in candidates:
        if os.path.exists(reg) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont(name, reg))
            pdfmetrics.registerFont(TTFont(name + "-Bold", bold))
            return name, name + "-Bold"
    raise RuntimeError("Не найден TTF-шрифт с поддержкой кириллицы")


FONT, FONT_BOLD = register_fonts()


# ---------- соцподдержка ----------

FLAGS = [
    ("mentors", "Наставничество"),
    ("housing", "Жильё"),
    ("social_land", "Участок"),
    ("social_communal", "ЖКХ"),
    ("zemskii", "Земский"),
    ("social_rent", "Аренда"),
    ("social_mortgage", "Ипотека"),
    ("social_deposit", "Вклад"),
]


def support_text(row: dict[str, Any]) -> str:
    out = [label for key, label in FLAGS
           if str(row.get(key, "0")).strip() in ("1", "true", "True")]
    return ", ".join(out) if out else "—"


# ---------- классификация ----------

def classify(row: dict[str, Any]) -> str | None:
    spec = (row.get("speciality") or "").strip().lower()
    title = (row.get("title") or "").strip().lower()

    if spec == "врач":
        return "vuz"
    if spec in ("средний медицинский персонал", "младший медицинский персонал"):
        return "suz"
    if spec in ("административный персонал", "прочие"):
        return None
    if re.match(r"^(врач|заведующ)", title) or " врач" in title:
        return "vuz"
    if any(k in title for k in ("медицинская сестра", "фельдшер", "акушерк",
                                 "санитарк", "санитар ", "лаборант", "медсестра")):
        return "suz"
    return None


# ---------- чтение CSV ----------

def read_rows() -> list[dict[str, Any]]:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f) if any(v.strip() for v in r.values())]


# ---------- построение PDF ----------

def build_pdf(rows: list[dict[str, Any]], title: str, subtitle: str,
              description: str, out_path: Path) -> None:
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=15 * mm, bottomMargin=18 * mm,
        title=title,
        author=AUTHOR,
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName=FONT_BOLD,
                        fontSize=20, leading=24, alignment=1,
                        textColor=colors.HexColor("#1a3a5c"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName=FONT_BOLD,
                        fontSize=13, leading=16, alignment=1,
                        textColor=colors.HexColor("#2c3e50"), spaceAfter=8)
    body = ParagraphStyle("body", parent=styles["Normal"], fontName=FONT,
                          fontSize=10, leading=14, alignment=4)
    small = ParagraphStyle("small", parent=styles["Normal"], fontName=FONT,
                           fontSize=8.5, leading=11,
                           textColor=colors.HexColor("#555555"))
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontName=FONT,
                          fontSize=8, leading=10)
    cell_bold = ParagraphStyle("cell_bold", parent=cell, fontName=FONT_BOLD)

    by_area: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_area[(r.get("area") or "—").strip()].append(r)

    story: list[Any] = [
        Paragraph(escape(title), h1),
        Paragraph(escape(subtitle), h2),
        Spacer(1, 4 * mm),
        Paragraph(description, body),
        Spacer(1, 6 * mm),
        Paragraph(
            f"Всего вакансий: <b>{len(rows)}</b>. "
            f"Источник: <i>{escape(AUTHOR)}</i>. "
            f"Дата формирования: {datetime.now().strftime('%d.%m.%Y')}.",
            small,
        ),
        Spacer(1, 6 * mm),
    ]

    header = ["№", "Должность", "Медицинская организация",
              "Кол-во", "Социальная поддержка"]
    data: list[list[Any]] = [header]
    section_rows: list[int] = []
    n = 0

    for area in sorted(by_area.keys()):
        section_rows.append(len(data))
        data.append([Paragraph(f"<b>{escape(area)}</b>", cell_bold),
                     "", "", "", ""])

        for r in sorted(by_area[area],
                        key=lambda x: ((x.get("organization") or "").lower(),
                                       (x.get("title") or "").lower())):
            n += 1
            data.append([
                str(n),
                Paragraph(escape(r.get("title") or "—"), cell),
                Paragraph(escape(r.get("organization") or "—"), cell),
                (r.get("qty") or "—").strip() or "—",
                Paragraph(escape(support_text(r)), cell),
            ])

    col_widths = [8 * mm, 80 * mm, 90 * mm, 15 * mm, 80 * mm]

    style: list[Any] = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bdc3c7")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]

    for i in section_rows:
        style += [
            ("SPAN", (0, i), (-1, i)),
            ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#d6e4f0")),
            ("TEXTCOLOR", (0, i), (-1, i), colors.HexColor("#1a3a5c")),
            ("FONTSIZE", (0, i), (-1, i), 10),
        ]

    data_rows = [i for i in range(1, len(data)) if i not in section_rows]
    for j, i in enumerate(data_rows):
        if j % 2 == 1:
            style.append(("BACKGROUND", (0, i), (-1, i),
                          colors.HexColor("#f5f8fb")))

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(style))
    story.append(t)

    def on_page(canvas, doc_):
        canvas.saveState()
        canvas.setFont(FONT, 8)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.drawString(12 * mm, 10 * mm, AUTHOR)
        canvas.drawRightString(A4[1] - 12 * mm, 10 * mm, f"стр. {doc_.page}")
        canvas.setStrokeColor(colors.HexColor("#cccccc"))
        canvas.line(12 * mm, 14 * mm, A4[1] - 12 * mm, 14 * mm)
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)


# ---------- main ----------

def main() -> None:
    rows = read_rows()
    vuz = [r for r in rows if classify(r) == "vuz"]
    suz = [r for r in rows if classify(r) == "suz"]

    desc_vuz = (
        "В документе собраны актуальные вакансии для врачей в медицинских "
        "организациях Краснодарского края. Вакансии сгруппированы по муниципальным "
        "образованиям. В графе «Социальная поддержка» указаны меры, доступные при "
        "трудоустройстве: служебное жильё, компенсация аренды, выплаты по программам "
        "«Земский доктор» и другие."
    )
    desc_suz = (
        "В документе собраны актуальные вакансии для среднего и младшего медицинского "
        "персонала в медицинских организациях Краснодарского края. Вакансии сгруппированы "
        "по муниципальным образованиям. В графе «Социальная поддержка» указаны меры, "
        "доступные при трудоустройстве: служебное жильё, компенсация аренды, выплаты "
        "по программе «Земский фельдшер» и другие."
    )

    build_pdf(
        vuz,
        "Вакансии для выпускников медицинских вузов",
        "Краснодарский край • Региональный кадровый центр",
        desc_vuz,
        OUT_DIR / "vacancies_vuz.pdf",
    )
    build_pdf(
        suz,
        "Вакансии для выпускников медицинских колледжей",
        "Краснодарский край • Региональный кадровый центр",
        desc_suz,
        OUT_DIR / "vacancies_suz.pdf",
    )

    print(f"ВУЗ: {len(vuz)} вакансий -> {OUT_DIR / 'vacancies_vuz.pdf'}")
    print(f"СУЗ: {len(suz)} вакансий -> {OUT_DIR / 'vacancies_suz.pdf'}")


if __name__ == "__main__":
    main()