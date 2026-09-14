#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_examples.py — جلب أمثلة من مصادر مفتوحة (قرآن وحديث) لأجل التركيب.

All endpoints tested live from the dataset folder; stdlib only (urllib).

Sources:
  Quran text     : https://api.alquran.cloud/v1/ayah/{ref}/{edition}        (no key)
  Word-by-word   : https://api.qurancdn.com/api/qdc/verses/by_key/{key}?words=true&word_fields=text_uthmani&translations=131
  Quran (CDN)    : https://cdn.jsdelivr.net/gh/fawazahmed0/quran-api@1/editions/...
  Hadith (CDN)   : https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/{edition}/hadiths/{n}.json  (no key)
  Hadith (keyed) : api.sunnah.com/v1  (free key), hadithapi.com  (free key)

Commands:
  ayah 2:153 [--edition quran-uthmani]     print ayah text + metadata
  wbw   2:153                              word-by-word table (uthmani + translation)
  hadith bukhari 1 [--edition ara-bukhari] print hadith text + metadata
  candidate 2:153                          emit a sentences.json-ready record draft
                                           (text + source) for you to annotate and add
"""
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent

UA = {"User-Agent": "nahw-dataset/1.0 (tarkeeb examples fetcher)"}


def get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def ayah_key(ref):
    """'2:153' or '2/153' or '2 153' -> ('2', '153')."""
    for sep in (":", "/", " "):
        if sep in ref:
            a, b = ref.replace(":", sep).split(sep)
            return a.strip(), b.strip()
    raise SystemExit("verse reference must be like 2:153")


def cmd_ayah(ref, edition="quran-uthmani"):
    a, v = ayah_key(ref)
    d = get("https://api.alquran.cloud/v1/ayah/%s:%s/%s" % (a, v, edition))
    data = d["data"]
    print("【%s:%s】 %s — %s" % (a, v, data["surah"]["englishName"], edition))
    print(data["text"])
    return 0


def cmd_wbw(ref):
    a, v = ayah_key(ref)
    d = get("https://api.qurancdn.com/api/qdc/verses/by_key/%s:%s"
            "?words=true&word_fields=text_uthmani&translations=131" % (a, v))
    verse = d.get("verse", {})
    print("【%s:%s】 %s" % (a, v, verse.get("text_uthmani")))
    print()
    for w in verse.get("words") or []:
        if w.get("char_type_name") and w["char_type_name"] != "word":
            continue
        tr = (w.get("translation") or {}).get("text", "")
        print("%3d  %-28s %s" % (w.get("position", 0), w.get("text_uthmani", ""), tr))
    return 0


def cmd_hadith(name, number, edition=None):
    ed = edition or ("ara-bukhari" if name.lower().startswith("bukh") else "ara-" + name.lower())
    d = get("https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/%s/%s.json" % (ed, number))
    h = (d.get("hadiths") or [None])[0]
    if not h:
        print("no hadith %s in %s" % (number, ed))
        return 1
    meta = d.get("metadata", {})
    print("【%s — %s】 hadith %s" % (meta.get("name", name), meta.get("section", {}).get("1", ""), h.get("hadithnumber")))
    print(h.get("text"))
    if h.get("grades"):
        print("grades:", h["grades"])
    return 0


def cmd_candidate(ref, edition="quran-uthmani"):
    """Emit a sentences.json-ready draft: you add translit/gloss/words/structure."""
    a, v = ayah_key(ref)
    d = get("https://api.alquran.cloud/v1/ayah/%s:%s/%s" % (a, v, edition))["data"]
    simple = get("https://api.qurancdn.com/api/qdc/verses/by_key/%s:%s?fields=text_imlaei_simple" % (a, v))
    text = (simple.get("verse") or {}).get("text_imlaei_simple") or d["text"]
    record = {
        "id": "S0XX",
        "text_ar": text,
        "translit": "",
        "gloss_en": "",
        "source": {"type": "quran", "ref": "%s:%s" % (a, v), "edition": edition},
        "jumla": {"type": None},
        "purpose": {"category": "khabariyya"},
        "awamil": [],
        "words": [],
        "mahall_ar": None,
        "tarkeeb_ar": "",
        "structure": {"kind": None, "parts": []}
    }
    print(json.dumps(record, ensure_ascii=False, indent=2))
    print("\n# أكمِل الترجمة والكلمات والتركيب، ثم أضفه إلى nahw/sentences.json وشغّل:"
          "\n#   python3 nahw/tarkeeb.py validate && python3 nahw/tarkeeb.py test")
    return 0


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    opts = [a for a in argv[1:] if a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    cmd, rest = args[0], args[1:]
    edition = None
    for o in opts:
        if o.startswith("--edition="):
            edition = o.split("=", 1)[1]
    try:
        if cmd == "ayah":
            return cmd_ayah(rest[0], edition or "quran-uthmani")
        if cmd == "wbw":
            return cmd_wbw(rest[0])
        if cmd == "hadith":
            return cmd_hadith(rest[0], rest[1], edition)
        if cmd == "candidate":
            return cmd_candidate(rest[0], edition or "quran-uthmani")
    except Exception as e:
        print("fetch error:", e)
        return 1
    print("unknown command:", cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
