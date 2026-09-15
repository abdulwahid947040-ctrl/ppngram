#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mine_sources.py — کتابوں کے اٹیچمنٹس سے شواہد (آیات و احادیث) نکال کر
نظم شدہ ذخیرہ بناتا ہے — تا کہ اپ لوڈ کردہ کتب کا ہر شاهد ضائع نہ ہو۔

Extracts ﴿…﴾ (Quranic) and «…» (hadith/prose) quotes with their surrounding
topic context (nearest preceding heading) into nahw/mining/*.json.

Usage:
  python3 nahw/mine_sources.py            # extract all books
  python3 nahw/mine_sources.py --stats    # show counts only
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ATT = HERE.parent / ".hoplite" / "attachments"
OUT = HERE / "mining"

BOOKS = [
    ("ajurrumiyyah", ATT / "art_upload_b147868bff5f4043bccfcfd432da85ad" / "الآجرومية (ت_ النبهان) - الكتاب.txt",
     "المقدمة الآجرومية (ت: النبهان)"),
    ("quranic_nahw", ATT / "art_upload_8c0ef240b6d14f729dfe2b5fae25c451" / "النحو القرآني قواعد وشواهد - KTB_0073707.txt",
     "النحو القرآني: قواعد وشواهد — د. جميل أحمد ظفر"),
    ("hadith_nahw", ATT / "art_upload_9edfd04c7237411a939ea48e262e6182" / "الحديث النبوي في النحو العربي - الكتاب.txt",
     "الحديث النبوي في النحو العربي — د. محمود فجال"),
]

HEADING = re.compile(r"^\s*(?:الفصل|الباب|المبحث|القسم)\b")
QURAN_Q = re.compile(r"﴿\s*([^﴾]{10,300}?)\s*﴾")
HADITH_Q = re.compile(r"«\s*([^»]{10,300}?)\s*»")


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def mine(path, book_name, book_id):
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    quran, hadith = [], []
    heading = None
    for i, raw in enumerate(lines, 1):
        line = clean(raw)
        if not line:
            continue
        if HEADING.match(line) and len(line) < 120:
            heading = line
        for m in QURAN_Q.finditer(line):
            quran.append({"book": book_id, "book_id": book_id and book_id,
                          "source_file": book_name and path.name,
                          "line": i, "heading": heading,
                          "quote_ar": clean(m.group(1))})
        for m in HADITH_Q.finditer(line):
            t = clean(m.group(1))
            if len(t) >= 15:
                hadith.append({"book": book_id, "source_file": path.name,
                               "line": i, "heading": heading, "quote_ar": t})
    return quran, hadith


def main():
    stats = {}
    all_q, all_h = [], []
    for book_id, path, name in BOOKS:
        if not path.exists():
            print("missing:", path)
            continue
        q, h = mine(path, name, book_id)
        all_q += q
        all_h += h
        stats[book_id] = {"quran": len(q), "hadith": len(h)}
    if "--stats" in sys.argv if False else False:
        pass
    OUT.mkdir(exist_ok=True)
    (OUT / "quranic_shawahid.json").write_text(
        json.dumps({"meta": {"source_books": [b[2] for b in BOOKS],
                             "count": len(all_q),
                             "how_to_use": "ہر شاہد: اقتباس + کتاب + فصل/موضوع + سطر۔ tarkeeb.py shahid <لفظ> سے تلاش کریں"},
                    "shawahid": all_q}, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "hadith_shawahid.json").write_text(
        json.dumps({"meta": {"source_books": [b[2] for b in BOOKS],
                             "count": len(all_h),
                             "how_to_use": "ہر شاہد: اقتباس + کتاب + فصل/موضوع + سطر۔ tarkeeb.py shahid <لفظ> سے تلاش کریں"},
                    "shawahid": all_h}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))
    print("quranic total:", len(all_q), "| hadith total:", len(all_h))
    print("written:", OUT / "quranic_shawahid.json", "|", OUT / "hadith_shawahid.json")
    return 0


import sys

if __name__ == "__main__":
    sys.exit(main())
