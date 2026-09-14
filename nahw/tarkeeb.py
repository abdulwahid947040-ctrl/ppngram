#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tarkeeb.py — systematic nahw tool for the dataset in this folder.

Commands:
  validate              Check all dataset files for schema & reference consistency.
  parse "SENTENCE"      Assign each word its nahw place + whole-sentence tarkeeb.
  corpus [ID]           List / show annotated corpus sentences.
  test                  Parse every corpus sentence and diff against annotations.

Options:
  --json                Machine-readable output (parse / test).

Scope: a lexicon-driven rule engine covering the structures in sentences.json
(nominal & verbal sentences, kana/inna group, jar & majrur, na't, atf, shart,
istithna, nida, nahy, amr, istifham, pronoun suffixes). Extend lexicon.json to
cover more words — this is a data-driven seed, not a full morphological analyzer.
"""
import json
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent

PUNCT = "؟،.؛!?;:"
MARKS = set("ًٌٍَُِّْ")

CASE_NAMES = {"raf": "مرفوع", "nasb": "منصوب", "jarr": "مجرور", "jazm": "مجزوم"}
CASE_OWN = {"raf": "رفعه", "nasb": "نصبه", "jarr": "جره"}
KIND_AR = {"ishara": "اسم إشارة", "mawsul": "اسم موصول", "damir": "ضمير",
           "istifham": "اسم استفهام", "zarf": "ظرف", "munada": "منادى"}
NOUN_SUFFIXES = ["هما", "كما", "هن", "هم", "كم", "ها", "نا", "ك", "ه"]
VERB_OBJ_SUFFIXES = ["هما", "هن", "هم", "ها", "نا", "ه"]


def load(name):
    with open(HERE / name, encoding="utf-8") as f:
        return json.load(f)


def strip_marks(s):
    # "نورًا" strips to "نورا" — drop the tanween with its trailing alif first;
    # normalize alef maqsura and hamza carriers so keys and lookups match
    s = s.replace("ًا", "ً").replace("ى", "ي").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    return "".join(ch for ch in s if ch not in MARKS and unicodedata.category(ch) != "Mn")


def last_mark(surface):
    # shadda is a doubling sign, never an i'rab mark — skip it
    mark = None
    for ch in surface:
        if ch in MARKS and ch != "ّ":
            mark = ch
    return mark


def case_hint(surface):
    m = last_mark(surface)
    if m in ("ٌ", "ُ"):
        return "raf"
    if m in ("ً", "َ"):
        return "nasb"
    if m in ("ٍ", "ِ"):
        return "jarr"
    if m == "ْ":
        return "sukun"
    return None


def sign_of(surface, case):
    m = last_mark(surface)
    if case == "raf":
        return "الضمة الظاهرة (تنوين)" if m == "ٌ" else "الضمة الظاهرة"
    if case == "nasb":
        if m == "ً":
            return "الفتحة الظاهرة (تنوين)"
        if m == "ِ":
            return "الكسرة نيابة عن الفتحة"
        return "الفتحة الظاهرة"
    if case == "jarr":
        if m == "ٍ":
            return "الكسرة الظاهرة (تنوين)"
        if m == "َ":
            return "الفتحة لأنه ممنوع من الصرف"
        return "الكسرة الظاهرة"
    return "السكون"


def tokenize(text):
    toks = []
    for chunk in text.split():
        i, j = 0, len(chunk)
        while i < j and chunk[i] in PUNCT:
            toks.append(("punct", chunk[i]))
            i += 1
        k = j
        while k > i and chunk[k - 1] in PUNCT:
            k -= 1
        if k > i:
            toks.append(("word", chunk[i:k]))
        while k < j:
            toks.append(("punct", chunk[k]))
            k += 1
    return toks


class Index:
    def __init__(self, lex):
        self.words = {}
        self.verbs = {}
        for key, e0 in lex["entries"].items():
            e = dict(e0)
            e["key"] = key
            kb = strip_marks(key)
            self.words[kb] = e
            if e.get("class") == "fil":
                # passives first so active forms win on identical surface
                for form in ("madi_passive", "mudari_passive", "madi", "mudari", "amr"):
                    if e.get(form):
                        self.verbs[strip_marks(e[form])] = (kb, form)
            if e.get("class") == "ism" and not kb.startswith("ال"):
                self.words.setdefault("ال" + kb, e)

    def noun(self, bare):
        e = self.words.get(bare)
        if not e and bare.startswith("ال"):
            e = self.words.get(bare[2:])
        return e if e and e.get("class") == "ism" else None

    def harf(self, bare):
        e = self.words.get(bare)
        return e if e and e.get("class") == "harf" else None

    def verb(self, bare):
        return self.verbs.get(bare)


def resolve(index, surface):
    """Split one written token into resolvable parts (prefix/suffix aware)."""
    parts = []

    def candidates(rest):
        c = [rest]
        if len(rest) > 1 and rest.endswith(("و", "ى", "ا")):
            c.append(rest[:-1])
        return c

    def try_parse(bare, suffix=None):
        e = index.words.get(bare)
        if e and e.get("class") == "ism":
            return [{"noun": e, "suffix": suffix}]
        if e and e.get("class") == "harf":
            return [{"harf": e}]
        v = index.verb(bare)
        if v:
            return [{"verb": v, "suffix": suffix}]
        if bare.endswith("ت") and index.verb(bare[:-1]):
            return [{"verb": index.verb(bare[:-1]), "subject_t": True, "suffix": suffix}]
        if bare.endswith("نا") and len(bare) > 2 and index.verb(bare[:-2]):
            return [{"verb": index.verb(bare[:-2]), "subject_na": True, "suffix": suffix}]
        for end in ("ون", "ين", "ان"):
            if bare.endswith(end) and len(bare) > 2:
                v = index.verb(bare[:-2])
                if v and v[1] == "mudari":
                    return [{"verb": v, "khamsa": True, "suffix": suffix}]
        for s in NOUN_SUFFIXES:
            if len(bare) > len(s) and bare.endswith(s):
                r = try_parse(bare[:-len(s)], suffix or ("ism_suffix", s))
                if r:
                    return r
        for s in VERB_OBJ_SUFFIXES:
            if len(bare) > len(s) and bare.endswith(s):
                base_verb = index.verb(bare[:-len(s)])
                if base_verb:
                    return [{"verb": base_verb, "suffix": suffix or ("obj_suffix", s)}]
        if len(bare) > 1 and bare[0] in "بلك":
            assimilated = (bare[0] == "ل" and len(bare) > 2 and bare[1] == "ل")
            cands = candidates("ال" + bare[2:]) + candidates(bare[1:]) if assimilated else candidates(bare[1:])
            for cand in cands:
                r = try_parse(cand)
                if r:
                    head = [{"harf": index.words[bare[0]]}]
                    if assimilated and r and "noun" in r[0]:
                        head[0]["assimilated"] = True
                    return head + r
        if len(bare) > 1 and bare[0] in "وف":
            for cand in candidates(bare[1:]):
                r = try_parse(cand)
                if r:
                    fb = {"class": "harf", "kind": "huruf_atf", "key": bare[0]}
                    return [{"harf": index.words.get(bare[0]) or fb}] + r
        return None

    parts = try_parse(strip_marks(surface)) or [{"unknown": True}]
    if len(parts) == 1:
        parts[0]["surface"] = surface
    elif parts[0].get("assimilated"):
        parts[0]["surface"] = surface[:1]
        rest = "ال" + surface[2:]
        if len(parts) == 2:
            parts[1]["surface"] = rest
        else:
            for p in parts[1:]:
                p["surface"] = rest
    else:
        cut = 2 if len(surface) > 1 and unicodedata.category(surface[1]) == "Mn" else 1
        parts[0]["surface"] = surface[:cut]
        rest = surface[cut:]
        if len(parts) == 2:
            parts[1]["surface"] = rest
        else:
            for p in parts[1:]:
                p["surface"] = rest
    return parts


class State:
    def __init__(self):
        self.pending_jarr = False
        self.shibh = []
        self.nasikh = None
        self.nasikh_kind = None
        self.nasikh_stage = 0
        self.expect = None
        self.main_verb = None
        self.sila = False
        self.sila_verb = None
        self.jawab_pending = False
        self.jawab_bi_fa = False
        self.jazm_pending = False
        self.jazm_kind = None
        self.shart = False
        self.shart_verb = None
        self.nida = False
        self.istithna = False
        self.q_zarf = False
        self.q_man = False
        self.q_zarf_unit = None
        self.atf_pending = False
        self.tamyiz_pending = False
        self.nai_b = False
        self.words_after = 0
        self.purpose = None
        self.mubtada = None
        self.khabar = None
        self.last_ism = None
        self.khabar_jumla = False
        self.nothing_yet = True


class Parser:
    def __init__(self, index):
        self.index = index

    def parse(self, text):
        self.units = []
        self.st = st = State()
        tokens = tokenize(text)
        word_positions = [i for i, (k, _) in enumerate(tokens) if k == "word"]
        for idx, (kind, surf) in enumerate(tokens):
            st.words_after = sum(1 for wp in word_positions if wp > idx)
            if kind == "punct":
                if surf == "؟" and st.purpose is None:
                    st.purpose = ("inshiyya", "istifham")
                continue
            parts = resolve(self.index, surf)
            if parts and parts[0].get("harf"):
                key = parts[0]["harf"].get("key")
                nxt = self._next_cls(tokens, idx)
                if key == "ما":
                    parts[0] = dict(parts[0])
                    parts[0]["as_nafiya"] = (nxt == "fil")
                    parts[0]["as_istifham"] = (nxt != "fil")
                elif key == "من" and st.nothing_yet and nxt == "fil":
                    parts[0] = dict(parts[0])
                    parts[0]["q_man"] = True
            for part in parts:
                part["next_hint"] = case_hint(next((s2 for k2, s2 in tokens[idx + 1:] if k2 == "word"), ""))
                self.consume(part)
            st.nothing_yet = False
        return self.finish(text)

    def _next_cls(self, tokens, idx):
        for k2, s2 in tokens[idx + 1:]:
            if k2 == "punct":
                continue
            parts = resolve(self.index, s2)
            if not parts:
                return None
            p = parts[0]
            if "noun" in p or "unknown" in p:
                return "ism"
            if "verb" in p:
                return "fil"
            return "harf"
        return None

    def add_unit(self, p, cls, kind, case, mabni=False, mahall=None):
        u = {"i": len(self.units) + 1, "tok": p.get("tok"), "surface_ar": p.get("surface"),
             "class": cls, "kind": kind, "case": case, "mabni": mabni, "mahall": mahall,
             "sign_ar": None, "irab_ar": "", "gloss_en": (p.get("noun") or p.get("harf") or {}).get("en")}
        self.units.append(u)
        return u

    # ------------------------------------------------------------------ harf
    def consume_harf(self, p, entry):
        st = self.st
        kind = entry.get("kind")
        key = entry.get("key", "")
        if p.get("q_man"):
            u = self.add_unit(p, "ism", "istifham", "raf", mabni=True, mahall="fail")
            u["irab_ar"] = "اسم استفهام مبني على السكون في محل رفع فاعل"
            u["sign_ar"] = "السكون"
            st.q_man = True
            st.purpose = st.purpose or ("inshiyya", "istifham")
            return
        u = self.add_unit(p, "harf", kind, None, mabni=True)
        u["irab_ar"] = entry.get("irab_ar") or "حرف"
        if entry.get("purpose"):
            st.purpose = st.purpose or tuple(entry["purpose"])
        if kind == "ma_ambiguous":
            if p.get("as_nafiya"):
                u["irab_ar"] = "حرف نفي مبني على السكون"
                st.purpose = st.purpose or ("khabariyya", "nafi")
            else:
                u["irab_ar"] = "اسم استفهام مبني على السكون"
                st.purpose = st.purpose or ("inshiyya", "istifham")
        elif kind == "harf_jarr":
            st.pending_jarr = True
            st.shibh = [u["i"]]
        elif kind == "nawasikh_inna":
            st.nasikh = "inna"
            st.nasikh_kind = "inna"
            st.nasikh_stage = 0
        elif kind == "harf_jazm":
            st.jazm_pending = True
            if entry.get("sub") == "nahy":
                st.jazm_kind = "nahy"
                st.purpose = st.purpose or ("inshiyya", "nahy")
            elif key == "لم":
                st.jazm_kind = "lam"
                st.purpose = st.purpose or ("khabariyya", "nafi")
        elif kind == "adawat_shart_jazima":
            st.shart = True
            st.shart_verb = None
            st.jawab_pending = False
            st.purpose = st.purpose or ("shartiyya", None)
        elif kind == "harf_istithna":
            st.istithna = True
            if st.expect == "fail" and st.main_verb:
                st.main_verb["irab_ar"] += "، والفاعل ضمير مستتر جوازًا تقديره «هُوَ»"
            st.expect = None
        elif kind == "huruf_nida":
            st.nida = True
            st.purpose = st.purpose or ("inshiyya", "nida")
        elif kind == "huruf_atf":
            if st.shart and key == "ف":
                u["irab_ar"] = "الفاء واقعة في جواب الشرط: حرف عطف"
                st.jawab_pending = True
                st.jawab_bi_fa = True
            else:
                st.atf_pending = True
        elif kind == "huruf_istifham":
            st.purpose = st.purpose or ("inshiyya", "istifham")

    # ------------------------------------------------------------------- fil
    def consume_verb(self, p, key, form):
        st = self.st
        entry = self.index.words[key]
        u = self.add_unit(p, "fil", form, None, mabni=(form != "mudari"))
        u["_key"] = key
        if entry.get("naqis"):
            st.nasikh = "kana"
            st.nasikh_kind = "kana"
            st.nasikh_stage = 0
            u["irab_ar"] = "فعل ماضٍ ناقص مبني على الفتح"
            u["sign_ar"] = "الفتح"
            return
        transitive = bool(entry.get("transitive"))
        passive = form.endswith("_passive")
        if not passive and form == "madi" and entry.get("madi_passive"):
            # كُتِبَ: damma early + kasra later marks the passive stem
            s = p.get("surface", "")
            i_d, i_k = s.find("ُ"), s.find("ِ")
            if 0 <= i_d < i_k:
                passive = True
                form = "madi_passive"
                u["kind"] = "madi_majhul"
        if passive:
            st.nai_b = True
            if form.endswith("_passive"):
                u["kind"] = form.replace("_passive", "_majhul")
        in_jawab = st.jawab_pending
        in_jawab_bi_fa = st.jawab_bi_fa

        if in_jawab:
            u["mahall"] = None
            st.jawab_pending = False
            st.shart = False
            st.jawab_bi_fa = False
            st.expect = "maful" if (transitive and not p.get("suffix")) else None
        elif st.mubtada is not None and st.main_verb is None and not st.sila:
            st.khabar_jumla = True
            st.main_verb = u
            st.expect = "maful" if transitive else None
        elif st.sila and st.sila_verb is None:
            st.sila_verb = u
            st.expect = "maful" if transitive else None
        elif st.main_verb is None:
            st.main_verb = u
            # a verb after ism-inna acts as its khabar — the nasikh is consumed
            st.nasikh = None
            if st.shart:
                st.shart_verb = u
            if passive:
                st.expect = "fail"
            elif p.get("subject_t") or st.q_man:
                st.expect = "maful" if transitive else None
            elif st.jazm_kind == "nahy":
                u["irab_ar"] += "، والفاعل ضمير مستتر تقديره «أنتَ»"
                st.expect = "maful" if transitive else None
            elif form == "amr":
                u["irab_ar"] += "، والفاعل ضمير مستتر تقديره «أنتَ»"
                st.expect = "maful" if transitive else None
            elif st.last_ism is not None:
                # a noun already stood before the verb (e.g. ism of inna/kana):
                # the doer is hidden by obligation (estimation = that noun)
                u["irab_ar"] += "، والفاعل ضمير مستتر وجوبًا تقديره «%s»" % st.last_ism["surface_ar"]
                st.expect = "maful" if transitive else None
            else:
                st.expect = "fail"
        else:
            st.main_verb = u
            st.expect = "fail"

        if form == "mudari":
            jussive = st.jazm_pending or (in_jawab and not in_jawab_bi_fa)
            if jussive:
                u["case"] = "jazm"
                if p.get("khamsa"):
                    u["sign_ar"] = "حذف النون"
                    u["irab_ar"] = "فعل مضارع مجزوم وعلامة جزمه حذف النون لأنه من الأفعال الخمسة"
                else:
                    u["sign_ar"] = ("السكون" if "ْ" in p.get("surface", "")
                                    else "حذف حرف العلة")
                    u["irab_ar"] = "فعل مضارع مجزوم وعلامة جزمه " + u["sign_ar"]
            else:
                u["case"] = "raf"
                if p.get("khamsa"):
                    u["sign_ar"] = "ثبوت النون"
                    u["irab_ar"] = "فعل مضارع مرفوع بثبوت النون لأنه من الأفعال الخمسة"
                else:
                    u["sign_ar"] = "الضمة الظاهرة"
                    u["irab_ar"] = "فعل مضارع مرفوع لعدم وجود ناصب ولا جازم وعلامة رفعه الضمة الظاهرة"
            st.jazm_pending = False
            st.jazm_kind = None
        else:
            st.jazm_pending = False
            st.jazm_kind = None
            if form == "amr":
                u["sign_ar"] = "السكون"
                u["irab_ar"] = "فعل أمر مبني على السكون"
            elif passive:
                u["sign_ar"] = "الفتح"
                u["irab_ar"] = "فعل ماضٍ مبني للمجهول مبني على الفتح"
            elif p.get("subject_t") or p.get("subject_na"):
                pron = "والتاء" if p.get("subject_t") else "والنا"
                u["sign_ar"] = "السكون"
                u["irab_ar"] = "فعل ماضٍ مبني على السكون لاتصاله بضمير رفع متحرك، %s ضمير متصل مبني في محل رفع فاعل" % pron
            else:
                u["sign_ar"] = "الفتح"
                u["irab_ar"] = "فعل ماضٍ مبني على الفتح"
        if in_jawab_bi_fa:
            u["irab_ar"] = "جواب الشرط مقترنًا بالفاء فلا محل له من الإعراب؛ " + u["irab_ar"]
        if st.khabar_jumla and st.main_verb is u:
            if p.get("khamsa"):
                u["irab_ar"] += "، والواو ضمير متصل مبني في محل رفع فاعل"
            elif not (p.get("subject_t") or p.get("subject_na")):
                u["irab_ar"] += "، والفاعل ضمير مستتر وجوبًا تقديره «%s»" % st.mubtada["surface_ar"]
            st.khabar_jumla = False

    # ------------------------------------------------------------------- ism
    def consume_ism(self, p, entry):
        st = self.st
        kind = (entry or {}).get("kind")
        if entry and entry.get("special") == "q_man":
            u = self.add_unit(p, "ism", "istifham", "raf", mabni=True, mahall="fail")
            u["irab_ar"] = "اسم استفهام مبني على السكون في محل رفع فاعل"
            u["sign_ar"] = "السكون"
            st.q_man = True
            st.purpose = st.purpose or ("inshiyya", "istifham")
            return
        if entry and entry.get("special") == "q_zarf":
            u = self.add_unit(p, "ism", "istifham", "nasb", mabni=True, mahall="maful_fih")
            u["irab_ar"] = "اسم استفهام مبني على السكون في محل نصب مفعول فيه (ظرف) متعلق بخبر مقدم"
            u["sign_ar"] = "السكون"
            st.q_zarf = True
            st.q_zarf_unit = u
            st.purpose = st.purpose or ("inshiyya", "istifham")
            return
        if entry and entry.get("kind") == "mawsul":
            u = self.add_unit(p, "ism", "mawsul", "raf", mabni=True, mahall="fail")
            u["irab_ar"] = "اسم موصول مبني على السكون في محل رفع فاعل"
            u["sign_ar"] = "السكون"
            st.sila = True
            st.last_ism = u
            return

        surface = p.get("surface", "")
        hint = case_hint(surface)
        role = None
        case = None
        mabni = bool(entry and entry.get("mabni")) or entry is None and False

        if st.pending_jarr:
            role, case = "ism_majrur", "jarr"
            st.pending_jarr = False
            st.shibh.append(len(self.units) + 1)
        elif st.nasikh == "kana":
            if st.nasikh_stage == 0:
                role, case = "ism_kana", "raf"
                st.nasikh_stage = 1
            else:
                role, case = "khabar_kana", "nasb"
                st.nasikh = None
        elif st.nasikh == "inna":
            if st.nasikh_stage == 0:
                role, case = "ism_inna", "nasb"
                st.nasikh_stage = 1
            else:
                role, case = "khabar_inna", "raf"
                st.nasikh = None
        elif st.nida:
            role, case, mabni = "munada", "nasb", True
            st.nida = False
        elif st.istithna:
            role, case = "mustathna", "nasb"
            st.istithna = False
        elif st.q_zarf and st.mubtada is None:
            role, case = "mubtada", "raf"
            st.q_zarf = False
        elif entry and entry.get("kind") == "number" and st.main_verb is not None:
            # 11–19 / decades after a transitive verb are its direct object
            role, case = "maful_bih", "nasb"
            st.expect = None
            st.tamyiz_pending = True
        elif st.tamyiz_pending and hint == "nasb":
            role, case = "tamyiz", "nasb"
            st.tamyiz_pending = False
        elif st.expect == "fail":
            if st.nai_b:
                role, case = "naib_fail", "raf"
                st.nai_b = False
            else:
                role, case = "fail", "raf"
            st.expect = "maful" if self._verb_transitive() else None
            if st.shart:
                st.jawab_pending = True
        elif st.expect == "maful":
            role, case = "maful_bih", "nasb"
            if self._verb_ditransitive():
                st.expect = "maful2"
            else:
                st.expect = None
        elif st.expect == "maful2":
            role, case = "maful_bih_thani", "nasb"
            st.expect = None
        elif entry and entry.get("masdar") and hint == "nasb" and \
                st.main_verb is not None and st.expect is None:
            role, case = entry.get("maful") or "maful_mutlaq", "nasb"
        elif st.atf_pending and st.last_ism:
            role = "atf"
            case = st.last_ism.get("case") or "raf"
            st.atf_pending = False
        elif entry and entry.get("kind") == "sifa" and self.units and \
                self.units[-1].get("class") == "ism" and hint is not None and \
                hint == self.units[-1].get("case") and \
                (st.khabar is not None or st.main_verb is not None or
                 (st.words_after >= 2 and p.get("next_hint") != "jarr")):
            role, case = "nat", self.units[-1]["case"]
        elif st.mubtada is None and st.main_verb is None and st.nasikh_kind is None:
            role, case = "mubtada", hint or "raf"
            if st.q_zarf:
                role = "mubtada"
        elif st.khabar is None and st.mubtada is not None and hint in ("raf", None):
            role, case = "khabar", "raf"
        elif hint == "jarr" and st.last_ism and st.last_ism.get("class") == "ism" and \
                (st.last_ism.get("mahall") != "ism_majrur" and st.last_ism.get("case") != "jarr"
                 or st.last_ism.get("mahall") == "mudaf_ilaihi"):
            role, case = "mudaf_ilaihi", "jarr"
            st.last_ism["irab_ar"] += " وهو مضاف"
            st.last_ism["extra"] = "mudaf"
        elif entry and entry.get("kind") == "zarf":
            role, case = "maful_fih", "nasb"
        else:
            case = hint

        u = self.add_unit(p, "ism", kind or "zahir", case, mabni=mabni, mahall=None)
        self._attach_mahall(u, role, case, surface, entry)
        if role == "mubtada":
            st.mubtada = u
        if role in ("khabar", "khabar_kana"):
            st.khabar = u
        st.last_ism = u
        if p.get("suffix") and p["suffix"][0] == "ism_suffix":
            s = p["suffix"][1]
            pron = {"ك": "الكاف", "كما": "الكاف", "كم": "الكاف", "ه": "الهاء",
                    "ها": "الهاء", "هما": "الهاء", "هم": "الهاء", "هن": "الهاء",
                    "نا": "النون"}.get(s, "الضمير")
            u["irab_ar"] += " وهو مضاف، و%s ضمير متصل مبني في محل جر مضاف إليه" % pron
        if role == "mubtada" and st.q_zarf_unit is not None:
            u["irab_ar"] = u["irab_ar"].replace("مبتدأ", "مبتدأ مؤخر")

    def _verb_transitive(self):
        v = self.st.main_verb
        if not v or not v.get("_key"):
            return False
        return bool(self.index.words[v["_key"]].get("transitive"))

    def _verb_ditransitive(self):
        v = self.st.main_verb
        if not v or not v.get("_key"):
            return False
        return bool(self.index.words[v["_key"]].get("ditransitive"))

    def _attach_mahall(self, u, role, case, surface, entry):
        pos_names = self.pos_names
        if role is None:
            u["irab_ar"] = "اسم %s" % CASE_NAMES.get(case, "")
            u["sign_ar"] = sign_of(surface, case) if case else None
            return
        name = pos_names.get(role, role)
        if name.startswith("ال") and len(name) > 2:
            name = name[2:]
        if role in ("nat", "atf"):
            prev = self.st.last_ism
            if role == "atf" and prev:
                u["irab_ar"] = "معطوف على «%s» %s" % (prev["surface_ar"], CASE_NAMES.get(case, ""))
                u["mahall"] = "atf"
            else:
                u["irab_ar"] = "نعت %s تابعه" % CASE_NAMES.get(case, "")
                u["mahall"] = "nat"
            u["sign_ar"] = sign_of(surface, case)
            return
        u["mahall"] = role
        if entry and entry.get("jam_mudhakkar_salim") and case in ("jarr", "nasb"):
            u["sign_ar"] = "الياء (لأنه جمع مذكر سالم)"
            irab = "%s %s" % (name, CASE_NAMES.get(case, ""))
            irab += " وعلامة %s الياء لأنه جمع مذكر سالم" % CASE_OWN[case]
            u["irab_ar"] = irab
            return
        if role == "munada":
            u["sign_ar"] = "الضم"
            u["irab_ar"] = "منادى مبني على الضم في محل نصب"
            return
        if u.get("mabni") and u["kind"] in KIND_AR:
            u["irab_ar"] = "%s مبني على %s في محل %s %s" % (
                KIND_AR[u["kind"]], sign_of(surface, case) if case else "ما يُرفع به",
                CASE_NAMES.get(case, ""), name)
        else:
            irab = "%s %s" % (name, CASE_NAMES.get(case, ""))
            if case:
                irab += " وعلامة %s %s" % (CASE_OWN[case], sign_of(surface, case))
            u["irab_ar"] = irab
        u["sign_ar"] = sign_of(surface, case) if case else u["sign_ar"]

    # ------------------------------------------------------------- dispatcher
    def consume(self, p):
        if "harf" in p:
            self.consume_harf(p, p["harf"])
        elif "verb" in p:
            key, form = p["verb"]
            self.consume_verb(p, key, form)
        else:
            self.consume_ism(p, p.get("noun"))

    # ----------------------------------------------------------------- finish
    def finish(self, text):
        st = self.st
        if st.expect == "fail" and st.main_verb:
            st.main_verb["irab_ar"] += "، والفاعل ضمير مستتر جوازًا تقديره «هُوَ»"
        if st.purpose is None:
            if st.main_verb and str(st.main_verb.get("kind", "")).startswith("amr"):
                st.purpose = ("inshiyya", "amr")
            else:
                st.purpose = ("khabariyya", None)
        if st.nasikh_kind == "inna":
            jumla = ("ismiyya", "ba_inna_wa_ikhawatiha")
        elif st.mubtada is not None:
            jumla = ("ismiyya", None)
        else:
            jumla = ("filiyya", "kana_wa_ikhawatiha" if st.nasikh_kind == "kana" else None)
        mahall_ar = self._sentence_mahall()
        tarkeeb = "، ".join("«%s» %s" % (u["surface_ar"], u["irab_ar"]) for u in self.units)
        if mahall_ar:
            tarkeeb += " " + mahall_ar + "."
        return {
            "text_ar": text,
            "jumla": {"type": jumla[0], "subtype": jumla[1]},
            "purpose": {"category": st.purpose[0], "subtype": st.purpose[1]},
            "words": self.units,
            "mahall_ar": mahall_ar,
            "tarkeeb_ar": tarkeeb,
        }

    def _sentence_mahall(self):
        st = self.st
        if st.q_zarf_unit is not None and st.mubtada is not None:
            return "«%s» في محل نصب متعلق بخبر مقدم، و«%s» مبتدأ مؤخر" % (
                st.q_zarf_unit["surface_ar"], st.mubtada["surface_ar"])
        if st.nasikh_kind == "inna" and st.main_verb is not None:
            return "الجملة الفعلية «%s» في محل رفع خبر إنّ" % self._verb_tail(st.main_verb)
        if st.main_verb is not None and any(u is st.main_verb for u in self.units) and \
                st.mubtada is not None and not st.sila:
            tail = self._verb_tail(st.main_verb)
            return "الجملة الفعلية «%s» في محل رفع خبر المبتدأ" % tail
        if st.sila and st.sila_verb is not None:
            return "جملة «%s» صلة الموصول، والموصول مع صلته في محل نصب نعت (صفة) للمبتدأ" % st.sila_verb["surface_ar"]
        if st.shibh:
            surfaces = " ".join(u["surface_ar"] for u in self.units if u["i"] in st.shibh)
            if st.main_verb is not None:
                return "شبه الجملة «%s» في محل نصب متعلقة بالفعل «%s»" % (surfaces, st.main_verb["surface_ar"])
            return "شبه الجملة «%s» في محل نصب متعلقة بخبر محذوف" % surfaces
        for u in self.units:
            if u["mahall"] == "maful_fih" and u["kind"] == "zarf" and st.main_verb is None:
                return "الظرف «%s» في محل نصب متعلق بخبر محذوف" % u["surface_ar"]
        if st.jawab_bi_fa or any("جواب الشرط مقترنًا بالفاء" in (u["irab_ar"] or "") for u in self.units):
            return "جملة الجواب جواب الشرط المقترن بالفاء فلا محل لها من الإعراب"
        return None

    def _verb_tail(self, verb):
        out = [verb["surface_ar"]]
        for u in self.units:
            if u["i"] > verb["i"] and u["class"] == "fil":
                break
            if u["i"] > verb["i"]:
                out.append(u["surface_ar"])
        return " ".join(out)


def build_parser():
    lex = load("lexicon.json")
    taxo = load("taxonomy.json")
    pos = load("positions.json")
    p = Parser(Index(lex))
    names = {}
    for c in pos["cases"]:
        for x in c["positions"]:
            names[x["id"]] = x["ar"]
    for x in pos["tawaabiat"]:
        names[x["id"]] = x["ar"]
    for x in pos["mudari_jazm"]["positions"]:
        names[x["id"]] = x["ar"]
    p.pos_names = names
    return p


# ------------------------------------------------------------------- validate
def cmd_validate():
    errors, warnings = [], []

    def err(msg):
        errors.append(msg)

    try:
        taxo = load("taxonomy.json")
    except Exception as e:
        err("taxonomy.json: %s" % e)
        taxo = None
    try:
        pos = load("positions.json")
    except Exception as e:
        err("positions.json: %s" % e)
        pos = None
    try:
        lex = load("lexicon.json")
    except Exception as e:
        err("lexicon.json: %s" % e)
        lex = None
    try:
        sen = load("sentences.json")["sentences"]
    except Exception as e:
        err("sentences.json: %s" % e)
        sen = None
    try:
        cur = load("curriculum.json")
    except Exception as e:
        err("curriculum.json: %s" % e)
        cur = None
    try:
        awd = load("awamil.json")
    except Exception as e:
        err("awamil.json: %s" % e)
        awd = None
    try:
        rld = load("rules.json")
    except Exception as e:
        err("rules.json: %s" % e)
        rld = None

    aw_ids = set()

    sentence_ids = set()
    if sen:
        sentence_ids = {s["id"] for s in sen}

    ids = set()

    def walk(node, path):
        if isinstance(node, dict):
            nid = node.get("id")
            if nid:
                if nid in ids:
                    err("taxonomy: duplicate id %s (%s)" % (nid, path))
                ids.add(nid)
            if nid and not node.get("ar"):
                err("taxonomy: node %s missing 'ar'" % nid)
            for k in ("children",):
                for ch in node.get(k, []) or []:
                    walk(ch, path + "/" + str(nid))
            for facet, items in (node.get("facets") or {}).items():
                for it in items:
                    walk(it, path + "/" + str(nid) + "#" + facet)
                    for t in it.get("types", []) or []:
                        walk(t, path + "/types")

    if taxo:
        walk(taxo["kalam"], "kalam")
        walk(taxo["kalima"], "kalima")

    pos_ids = set()
    if pos:
        for c in pos["cases"]:
            for s in c["signs"]:
                if s["id"] in pos_ids:
                    err("positions: duplicate sign id %s" % s["id"])
                pos_ids.add(s["id"])
            for x in c["positions"]:
                if x["id"] in pos_ids:
                    err("positions: duplicate position id %s" % x["id"])
                pos_ids.add(x["id"])
        for x in pos["tawaabiat"]:
            pos_ids.add(x["id"])
        for x in pos["mudari_jazm"]["positions"]:
            pos_ids.add(x["id"])

    if awd:
        for a in awd["awamil"]:
            if a["id"] in aw_ids:
                err("awamil: duplicate id %s" % a["id"])
            aw_ids.add(a["id"])
            for w in a.get("works_on", []):
                if w.get("mahall") and w["mahall"] not in pos_ids:
                    err("awamil %s: unknown mahall %s" % (a["id"], w["mahall"]))
        for ch in awd.get("chains", []):
            for e in ch.get("entrants", []):
                if e["id"] not in aw_ids:
                    err("awamil chains: unknown id %s" % e["id"])

    if rld:
        r_ids = set()
        for r in rld["irab_rules"]:
            if r["id"] in r_ids:
                err("rules: duplicate id %s" % r["id"])
            r_ids.add(r["id"])
            for a_id in r.get("if_awamil", []):
                if aw_ids and a_id not in aw_ids:
                    err("rules %s: unknown awamil id %s" % (r["id"], a_id))
            for t in r.get("then", []):
                if t.get("target_mahall") and t["target_mahall"] not in pos_ids:
                    err("rules %s: unknown mahall %s" % (r["id"], t["target_mahall"]))
                if t.get("case") not in (None, "raf", "nasb", "jarr", "jazm"):
                    err("rules %s: invalid case %r" % (r["id"], t.get("case")))

    # topics modules
    topics_dir = HERE / "topics"
    topic_ids = set()
    if topics_dir.exists():
        topic_ids = set()
        n_topics = 0
        for f in sorted(topics_dir.glob("*.json")):
            if f.name == "_index.json":
                continue
            try:
                with open(f, encoding="utf-8") as fh:
                    mod = json.load(fh)
            except Exception as e:
                err("topics/%s: %s" % (f.name, e))
                continue
            for t in mod.get("topics", []):
                n_topics += 1
                tid = t.get("id")
                if not tid:
                    err("topics/%s: topic missing id" % f.name)
                elif tid in topic_ids:
                    err("topics: duplicate id %s" % tid)
                else:
                    topic_ids.add(tid)
                for sh in t.get("shawahid", []):
                    if not (sh.get("source") and sh.get("text_ar")):
                        err("topics: %s shahid missing source/text" % tid)
        for f in sorted(topics_dir.glob("_index.json")):
            with open(f, encoding="utf-8") as fh:
                idx = json.load(fh)
            for m in idx.get("modules", []):
                for tid in m.get("topics", []):
                    if tid not in topic_ids:
                        err("topics index: unknown topic %s" % tid)
        print("topic modules:     %d (%d topics)" % (len(list(topics_dir.glob('module*.json'))), n_topics))

    # roadmap cross-references
    try:
        rd = load("roadmap.json")
        n_stages = len(rd.get("stages", []))
        bad = 0
        cur_ids = {lv["id"] for lv in cur["levels"]} if cur else set()
        for st in rd.get("stages", []):
            refs = st.get("refs", {})
            for tid in refs.get("topics", []):
                if tid not in topic_ids:
                    err("roadmap %s: unknown topic %s" % (st["id"], tid)); bad += 1
            for rid in refs.get("rules", []):
                if rid not in {r["id"] for r in rld["irab_rules"]}:
                    err("roadmap %s: unknown rule %s" % (st["id"], rid)); bad += 1
            for a_id in refs.get("awamil", []):
                if a_id not in aw_ids:
                    err("roadmap %s: unknown awamil %s" % (st["id"], a_id)); bad += 1
            for lv in refs.get("curriculum", []):
                if lv not in cur_ids:
                    err("roadmap %s: unknown level %s" % (st["id"], lv)); bad += 1
            for sid in refs.get("sentences", []):
                if sentence_ids and sid not in sentence_ids:
                    err("roadmap %s: unknown sentence %s" % (st["id"], sid)); bad += 1
        if "stages" in locals():
            print("roadmap stages:    %d (bad refs: %d)" % (n_stages, bad))
    except Exception as e:
        err("roadmap.json: %s" % e)

    n_entries = 0
    if lex:
        for key, e in lex["entries"].items():
            n_entries += 1
            if e.get("class") not in ("ism", "fil", "harf"):
                err("lexicon: %s invalid class %r" % (key, e.get("class")))
            if e.get("class") == "fil" and not any(e.get(f) for f in ("madi", "mudari", "amr")):
                err("lexicon: verb %s has no madi/mudari/amr" % key)
            if e.get("class") == "harf" and not e.get("kind"):
                err("lexicon: harf %s missing kind" % key)

    n_sen = 0
    n_words = 0
    if sen:
        seen = set()
        for s in sen:
            n_sen += 1
            sid = s["id"]
            if sid in seen:
                err("sentences: duplicate id %s" % sid)
            seen.add(sid)
            toks = []
            for chunk in s["text_ar"].split():
                bare = strip_marks("".join(ch for ch in chunk if ch not in PUNCT))
                if bare:
                    toks.append(bare)
            groups = {}
            for w in s["words"]:
                n_words += 1
                if w["class"] not in ("ism", "fil", "harf"):
                    err("%s: word %s invalid class" % (sid, w.get("i")))
                if w.get("case") not in (None, "raf", "nasb", "jarr", "jazm"):
                    err("%s: word %s invalid case %r" % (sid, w.get("i"), w.get("case")))
                if w.get("mahall") and w["mahall"] not in pos_ids:
                    err("%s: word %s unknown mahall %s" % (sid, w.get("i"), w["mahall"]))
                for a_id in s.get("awamil", []):
                    if a_id not in aw_ids:
                        err("%s: unknown awamil id %s" % (sid, a_id))
                if not w.get("irab_ar"):
                    err("%s: word %s missing irab_ar" % (sid, w.get("i")))
                groups.setdefault(w.get("tok") or w["i"], []).append(strip_marks(w["surface_ar"]))
            if list(groups.keys()) != list(range(1, len(toks) + 1)):
                err("%s: token grouping mismatch (words groups %s vs %s tokens)" % (sid, list(groups.keys()), len(toks)))
            else:
                for tk, parts in groups.items():
                    if "".join(parts).replace("لالل", "لل").replace("لال", "لل") != toks[tk - 1]:
                        err("%s: token %d surface mismatch %r != %r" % (sid, tk, "".join(parts), toks[tk - 1]))
            if s["jumla"]["type"] not in ("ismiyya", "filiyya"):
                err("%s: invalid jumla type" % sid)
            if s["purpose"]["category"] not in ("khabariyya", "inshiyya", "shartiyya"):
                err("%s: invalid purpose category" % sid)
            max_i = len(s["words"])

            def check_structure(node):
                for wref in node.get("words", []):
                    if not (1 <= wref <= max_i):
                        err("%s: structure references word %s out of range" % (sid, wref))
                for sub in node.get("parts", []):
                    check_structure(sub)
            check_structure(s["structure"])

    print("taxonomy nodes: %d" % len(ids))
    print("position ids:   %d" % len(pos_ids))
    print("lexicon keys:   %d" % n_entries)
    print("sentences:      %d (%d annotated words)" % (n_sen, n_words))
    n_levels = 0
    if cur:
        for lv in cur["levels"]:
            n_levels += 1
            for sid in lv.get("sentence_ids", []):
                if sentence_ids and sid not in sentence_ids:
                    err("curriculum: %s references unknown sentence %s" % (lv["id"], sid))
            for a_id in lv.get("awamil_ids", []):
                if aw_ids and a_id not in aw_ids:
                    err("curriculum: %s references unknown awamil %s" % (lv["id"], a_id))
            for ex in lv.get("inline_examples", []):
                for w in ex.get("words", []):
                    if w.get("mahall") and w["mahall"] not in pos_ids:
                        err("curriculum %s: unknown mahall %s" % (lv["id"], w["mahall"]))
        print("curriculum levels: %d" % n_levels)
    if awd:
        print("awamil entries:    %d (chains: %d sites)" % (len(aw_ids), len(awd.get("chains", []))))
    if rld:
        print("irab rules:        %d" % len(rld["irab_rules"]))
    for w in warnings:
        print("WARN:", w)
    if errors:
        print("\n%d ERROR(S):" % len(errors))
        for e in errors:
            print(" -", e)
        return 1
    print("\nOK — dataset consistent.")
    return 0


# ---------------------------------------------------------------- corpus cmds
def show_sentence(s):
    print("【%s】 %s" % (s["id"], s["text_ar"]))
    print("translit:", s["translit"])
    print("gloss:   ", s["gloss_en"])
    print("النوع:    جملة %s — %s%s" % (s["jumla"]["type"], s["purpose"]["category"],
          " / " + s["purpose"]["subtype"] if s["purpose"].get("subtype") else ""))
    print()
    print(" #  الكلمة        النوع              المحل            الإعراب")
    for w in s["words"]:
        print("%2d  %-12s  %-18s %-16s %s" % (
            w["i"], w["surface_ar"], w["class"] + "/" + (w.get("kind") or "-"),
            w.get("mahall") or "-", w["irab_ar"]))
    if s.get("mahall_ar"):
        print("\nالمحل:  ", s["mahall_ar"])
    print("\nالتركيب:", s["tarkeeb_ar"])


def cmd_corpus(sid=None):
    sen = load("sentences.json")["sentences"]
    if sid:
        for s in sen:
            if s["id"] == sid:
                show_sentence(s)
                return 0
        print("no sentence with id", sid)
        return 1
    for s in sen:
        print("%s  %s  — %s" % (s["id"], s["text_ar"], s["gloss_en"]))
    return 0


# ---------------------------------------------------------------------- parse
def cmd_parse(text, as_json=False):
    result = build_parser().parse(text)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print("الجملة:", text)
    purp = result["purpose"]["category"] + (" / " + result["purpose"]["subtype"] if result["purpose"]["subtype"] else "")
    print("النوع:  جملة %s — %s" % (result["jumla"]["type"], purp))
    if result["mahall_ar"]:
        print("المحل:  " + result["mahall_ar"])
    print()
    print(" #  الكلمة        النوع                المحل            الإعراب")
    for w in result["words"]:
        print("%2d  %-12s  %-18s %-16s %s" % (
            w["i"], w["surface_ar"], w["class"] + "/" + str(w.get("kind")),
            w.get("mahall") or "-", w["irab_ar"]))
    print("\nالتركيب:", result["tarkeeb_ar"])
    return 0


# ----------------------------------------------------------------------- test
def cmd_test(as_json=False):
    parser = build_parser()
    sen = load("sentences.json")["sentences"]
    total_words = 0
    total_checks = 0
    failed = []
    report = []
    for s in sen:
        if s.get("parser") is False:
            # manually annotated rich sentence beyond the rule engine
            report.append({"id": s["id"], "text": s["text_ar"], "status": "MANUAL", "failures": []})
            continue
        got = parser.parse(s["text_ar"])
        ws, gs = s["words"], got["words"]
        sen_fail = []
        if len(ws) != len(gs):
            sen_fail.append("unit count %d != %d" % (len(gs), len(ws)))
        for w, g in zip(ws, gs):
            total_words += 1
            if w["class"] != g["class"]:
                sen_fail.append("w%d class %s!=%s" % (w["i"], g["class"], w["class"]))
            if w.get("case") and w["case"] != g["case"]:
                sen_fail.append("w%d case %s!=%s" % (w["i"], g["case"], w["case"]))
            if w.get("mahall") and w["mahall"] != g.get("mahall"):
                sen_fail.append("w%d mahall %s!=%s" % (w["i"], g.get("mahall"), w["mahall"]))
        if s["jumla"]["type"] != got["jumla"]["type"]:
            sen_fail.append("jumla %s!=%s" % (got["jumla"]["type"], s["jumla"]["type"]))
        if s["purpose"]["category"] != got["purpose"]["category"]:
            sen_fail.append("purpose %s!=%s" % (got["purpose"]["category"], s["purpose"]["category"]))
        total_checks += 1
        status = "OK" if not sen_fail else "FAIL"
        report.append({"id": s["id"], "text": s["text_ar"], "status": status, "failures": sen_fail})
        if sen_fail:
            failed.append(s["id"])
            print("%s  %s" % (s["id"], s["text_ar"]))
            for f in sen_fail:
                print("   -", f)
    ok = len(sen) - len(failed)
    print("\ncorpus: %d/%d sentences fully agree; %d words compared" % (ok, len(sen), total_words))
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


# --------------------------------------------------------------------- awamil
def cmd_awamil(aid=None, show_chains=False):
    aw = load("awamil.json")
    by_id = {a["id"]: a for a in aw["awamil"]}
    if show_chains:
        for ch in aw["chains"]:
            print("【%s】 %s" % (ch["site_ar"], ch["base_ar"]))
            for e in ch["entrants"]:
                print("   ← %-38s %s" % (e["ar"], e["effect_ar"]))
            print()
        return 0
    if not aid:
        print("%-22s %-34s %s" % ("id", "العامل", "يعمل في"))
        for a in aw["awamil"]:
            print("%-22s %-34s %s" % (a["id"], a["ar"],
                  "، ".join(w["ar"] for w in a["works_on"])))
        print("\nالتفصيل: awamil <id>   |   سلاسل المواضع: awamil chains")
        return 0
    a = by_id.get(aid)
    if not a:
        print("no such awamil id:", aid)
        return 1
    print("【%s】 %s (%s)" % (a["id"], a["ar"], a["en"]))
    print("النوع:", aw["meta"]["type_values"].get(a["type"], a["type"]))
    for w in a["works_on"]:
        print("  يعمل في: %s ← %s%s" % (w["ar"], w["effect_ar"],
              " (%s)" % w["mahall"] if w.get("mahall") else ""))
    if a.get("members_ar"):
        print("الأعضاء:", "، ".join(a["members_ar"]))
    if a.get("example_ar"):
        print("مثال:", a["example_ar"])
    for n in a.get("notes_ar", []):
        print("ملاحظة:", n)
    sites = [ch["site_ar"] for ch in aw["chains"]
             if any(e["id"] == aid for e in ch["entrants"])]
    if sites:
        print("يأتي على:", "، ".join(sites))
    sen = load("sentences.json")["sentences"]
    hits = [s for s in sen if aid in s.get("awamil", [])]
    print("\nجمل مشروحة تحوي هذا العامل: %d" % len(hits))
    for s in hits:
        print("  %s  %s" % (s["id"], s["text_ar"]))
    return 0


# ----------------------------------------------------------------------- rules
def cmd_rules(rid=None):
    rl = load("rules.json")
    by_id = {r["id"]: r for r in rl["irab_rules"]}
    if not rid:
        print("%-24s %s" % ("id", "إن حدث هذا… سيحدث هذا"))
        for r in rl["irab_rules"]:
            print("%-24s %s" % (r["id"], r["if_ar"]))
        print("\nالتفصيل: rules <id>")
        return 0
    r = by_id.get(rid)
    if not r:
        print("no such rule id:", rid)
        return 1
    print("【%s】" % r["id"])
    print("الشرط:   ", r["if_ar"])
    print("الأثر:   ", r["then_ar"])
    for t in r["then"]:
        signs = (" — العلامات: " + "، ".join(t["signs_ar"])) if t.get("signs_ar") else ""
        print("   → %s (%s)%s" % (t["target_ar"], t.get("case") or "بلا إعراب", signs))
    print("مثال:    ", r["example_ar"])
    print("المصدر:  ", r["ajurrumiyyah_bab_ar"])
    return 0


# ----------------------------------------------------------------------- roadmap
def cmd_roadmap():
    rd = load("roadmap.json")
    mc = rd["mental_checklist"]
    print("【%s】" % mc["name_ar"])
    for q in mc["questions_ar"]:
        print("  %d) %s — %s" % (q["n"], q["q_ar"], q["how_ar"]))
        print("       (راجع: %s)" % q["see"])
    print()
    for st in rd["stages"]:
        print("【%s】 %s" % (st["id"], st["ar"]))
        print("   الهدف:", st["outcome_ar"])
        r = st["refs"]
        print("   الدراسة:", " | ".join(st["study_ar"]))
        tags = []
        if r.get("curriculum"): tags.append("مستويات: " + ", ".join(r["curriculum"]))
        if r.get("topics"): tags.append("موضوعات: " + ", ".join(r["topics"]))
        if r.get("rules"): tags.append("قواعد: " + ", ".join(r["rules"]))
        if r.get("awamil"): tags.append("عوامل: " + ", ".join(r["awamil"]))
        if r.get("sentences"): tags.append("جمل: " + ", ".join(r["sentences"]))
        for t in tags:
            print("   •", t)
        print()
    return 0


# ------------------------------------------------------------------------ quiz
def cmd_quiz():
    sen = load("sentences.json")["sentences"]
    import random
    s = random.choice(sen)
    print("【تدريب】 فكِّك هذه الجملة كلمةً كلمةً:")
    print("الجملة: %s" % s["text_ar"])
    if s.get("gloss_en"):
        print("المعنى: %s" % s["gloss_en"])
    if s.get("source"):
        print("المصدر: %s %s" % (s["source"].get("type"), s["source"].get("ref", "")))
    print("\nأسئلتك الستة: النوع؟ العامل؟ الأركان؟ الزوائد؟ المحالّ والعلامات؟ المحل الكلي؟")
    print("لعرض الحل: python3 nahw/tarkeeb.py corpus %s" % s["id"])
    return 0


def main(argv):
    args = [a for a in argv[1:] if a != "--json"]
    as_json = "--json" in argv
    if not args:
        print(__doc__)
        return 2
    cmd, rest = args[0], args[1:]
    if cmd == "validate":
        return cmd_validate()
    if cmd == "corpus":
        return cmd_corpus(rest[0] if rest else None)
    if cmd == "parse":
        if not rest:
            print('usage: tarkeeb.py parse "SENTENCE"')
            return 2
        return cmd_parse(" ".join(rest), as_json)
    if cmd == "test":
        return cmd_test(as_json)
    if cmd == "awamil":
        if rest and rest[0] == "chains":
            return cmd_awamil(show_chains=True)
        return cmd_awamil(rest[0] if rest else None)
    if cmd == "rules":
        return cmd_rules(rest[0] if rest else None)
    if cmd == "roadmap":
        return cmd_roadmap()
    if cmd == "quiz":
        return cmd_quiz()
    print("unknown command:", cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
