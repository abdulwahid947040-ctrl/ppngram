# nahw/ — البيانات النحوية المُنظَّمة | Systematic Arabic Nahw Dataset

A machine-readable collection of Arabic نحو (syntax) data, organized so that
**تَركِيب** (word-by-word grammatical parsing) becomes mechanical, and every
**whole sentence gets its place** (محل) in the structure.

Organized after the classical primers ( الآجُرُّوميّة، الكافية، هداية النحو ), with evidence (شواهد) drawn from the Quran and the Sunnah after «النحو القرآني: قواعد وشواهد» (د. جميل أحمد ظفر) and «الحديث النبوي في النحو العربي» (د. محمود فجال).

## Folder map

| File | What it holds |
|---|---|
| `taxonomy.json` | The whole conceptual tree: أقسام الكلام → الجملة (أنواعها، أغراضها، محالّها) → الكلمة (اسم/فعل/حرف بأنواعها) |
| `positions.json` | Every موضع إعرابي (فاعل، مفعول به، حال، …) with definition, sign, example — plus التوابع |
| `lexicon.json` | Seed lexicon (words → features) used by the parser |
| `sentences.json` | Annotated corpus: each word's إعراب + each sentence's full tarkeeb & structure tree |
| `curriculum.json` | منهاج متدرّج: 15 levels from the smallest sentence to the full-grown one, each mapped to its Ajurrumiyyah bāb, with the awāmil introduced and a growth map (words × awāmil) |
| `awamil.json` | فهرس العوامل: كل عامل لفظي (فعل/حرف) ومعنوي (الإضافة، الظرفية) — يعمل فيمَ وبأي إعراب وأعضاؤه + **سلاسل المواضع**: ما يأتي على المبتدأ والخبر والمضارع والاسم |
| `rules.json` | قواعد الأثر الشرطية (23 قاعدة): إن دخل هذا العامل… حصل هذا الإعراب — بالعلامات الممكنة ومثالها وبابها من الآجرومية، + قواعد مبني/مصرف/غير مصرف |
| `sources.md` | مصادر مفتوحة مُختبَرة (قرآن وحديث): واجهات API بلا مفتاح، وكلمة-بكلمة، وكيف تُضاف آية/حديث إلى بيانات التركيب |
| `fetch_examples.py` | أداة جلب الآيات والأحاديث من المصادر المفتوحة: `ayah / wbw / hadith / candidate` |
| `roadmap.json` | **خريطة الطريق الكاملة**: 6 مراحل دراسية تربط كل المكونات (مستويات + موضوعات + قواعد + عوامل + جمل)، مع «أسئلة الجملة الستة» التي يثبت الطالب هيكلها في ذهنه لأي جملة |
| `report.md` | الأدلة والقواعد: إحصاء كامل + جدول كل قاعدة بدليلها وبابها من الآجرومية |
| `topics/` | **الوحدات الموضوعية (10 وحدات، 29 موضوعًا)**: كل نوع جملة بمبنيه وشروطه وضوابطه وإعرابه التفصيلي ووجوه إعرابه وكيف يدخل في جملة أكبر + شواهد من القرآن والسنة + **تمثيلات من الحياة الطبيعية** للمواضع الصعبة — انظر `topics/_index.json` |
| `tarkeeb.py` | Tool: `validate`, `parse`, `corpus`, `test`, `awamil`, `rules`, `roadmap`, `quiz` |
| `templates/collection_template.csv` | One-row-per-word sheet for collecting your own tarkeeb data |

## العوامل والفلتر (awamil.json)

```bash
python3 nahw/tarkeeb.py awamil              # فهرس كل العوامل
python3 nahw/tarkeeb.py awamil kana_group   # تفصيل عامل + الجمل المشروحة التي فيه
python3 nahw/tarkeeb.py awamil chains       # سلاسل المواضع: ما يأتي على كل موضع
python3 nahw/tarkeeb.py rules               # قواعد الأثر: إن حدث هذا… سيحدث هذا (28 قاعدة)
python3 nahw/tarkeeb.py roadmap             # خريطة الطريق: المراحل وأسئلة الجملة الستة
python3 nahw/tarkeeb.py quiz                # تدريب: جملة عشوائية — فكّكها ثم اعرض الحل
python3 nahw/tarkeeb.py rules R_kana        # تفصيل قاعدة + علاماتها + بابها من الآجرومية
```

وقواعد البناء (في `rules.json` أيضًا):

- **مبني** (أنواعه ١٥ من باب الإعراب): لا يُعرب ولا يقبل علامات، ويأخذ محلّه من العمل (هذا: في محل رفع مبتدأ).
- **مصرف**: يُرفع بالضمة ويُنصب بالفتحة ويُجر بالكسرة، ويقبل التنوين وأل.
- **غير مصرف**: يُرفع بالضمة ويُنصب ويُجر بالفتحة، ولا يقبل التنوين — وأنواعه العشرة من باب الممنوع من الصرف: العلم (أحمد، عثمان، حمزة)، الصفة (أفعل، وما جُزم: كسلان)، الجمع (منتهى الجموع، معاليج)، اسم المفعول من غير الثلاثي (مُجمَّع)، المصدر الميمي (مجيء)، فَعَل (قُبح).

مثال — «ماذا يأتي على المبتدأ؟»:

```
【المبتدأ】 مرفوع (وهو أصل الجملة الاسمية)
   ← كان وأخواتها      ترفع المبتدأ فيصير اسم كان، وتنصب الخبر
   ← إنّ وأخواتها      تنصب المبتدأ فيصير اسم إنّ، وترفع الخبر
   ← ظنّ وأفعال القلوب  تنصب المبتدأ والخبر (مفعولان)
   ← لولا، لوما، لام الابتداء، لا النافية للجنس  تدخل بلا عمل
```

كل جملة في `sentences.json` تحمل حقل `"awamil"` بمعرّفات عواملها، وكل مستوى في `curriculum.json` يحمل `awamil_ids` — فتستطيع الفلترة: أعطني كل الجمل التي فيها «كان وأخواتها» أو «حروف الجر» أو «المبني للمجهول».

## How a sentence is broken down (data model)

```
sentence
├─ jumla:    {type: ismiyya | filiyya, subtype}
├─ purpose:  {category: khabariyya | inshiyya | shartiyya, subtype: amr | nahy | istifham | nida | nafi}
├─ words[]:  one record per word unit
│    class (ism/fil/harf) → kind (zahir, sifa, madi, harf_jarr, …)
│    → case (raf/nasb/jarr/jazm | mabni)
│    → mahall (position id from positions.json — the word's "place")
│    → sign_ar (علامة الإعراب) + irab_ar (full classical i'rab phrase)
├─ mahall_ar: where the WHOLE sentence sits (e.g. جملة فعلية في محل رفع خبر المبتدأ)
└─ structure: the sentence's parse tree (roles → word indices)
```

## Usage

```bash
python3 nahw/tarkeeb.py validate                     # consistency-check all data files
python3 nahw/tarkeeb.py parse "الطالبُ يقرأُ الكتابَ"  # word-by-word tarkeeb of any sentence
python3 nahw/tarkeeb.py parse "..." --json           # machine-readable output
python3 nahw/tarkeeb.py corpus                       # list the annotated corpus
python3 nahw/tarkeeb.py corpus S001                  # show one fully parsed sentence
python3 nahw/tarkeeb.py test                         # parser vs corpus self-test (43/43)
python3 nahw/fetch_examples.py wbw 2:153             # قرآن: كلمة بكلمة من المصادر المفتوحة
```

Example:

```
 #  الكلمة     النوع        المحل        الإعراب
 1  الطالبُ    ism/zahir    mubtada      مبتدأ مرفوع وعلامة رفعه الضمة الظاهرة
 2  يقرأُ      fil/mudari   -            فعل مضارع مرفوع… والفاعل ضمير مستتر وجوبًا تقديره «الطالبُ»
 3  الكتابَ    ism/zahir    maful_bih    مفعول به منصوب وعلامة نصبه الفتحة الظاهرة

المحل: الجملة الفعلية «يقرأُ الكتابَ» في محل رفع خبر المبتدأ
```

## The learning ladder (curriculum.json)

The student starts with the smallest sentence and sees **exactly what is added** at each step:

| Level | Example | Words | Awāmil | What was added |
|---|---|---|---|---|
| L01 | العلمُ نورٌ | 2 | 0 | مبتدأ + خبر مفرد |
| L02 | نجحَ الطالبُ | 2 | 1 | فعل + فاعل (العامل الأول) |
| L03 | الطالبُ في المسجدِ | 3 | 1 | حرف جر + مجرور (شبه جملة) |
| L04 | الجوُّ جميلٌ اليومَ | 3 | 1 | ظرف (مفعول فيه) |
| L05 | الطالبُ يقرأُ الكتابَ | 3 | 1 | فعل متعدٍّ + مفعول به |
| L06 | قرأَ الطالبُ كتابَ اللهِ | 4 | 2 | إضافة: مضاف + مضاف إليه |
| L07 | العلمُ نورٌ نافعٌ | 3 | 0 | موصوف + صفة (النعت تابع) |
| L08 | جاءَ زيدٌ وعمرٌو | 4 | 1 | التوابع: عطف/بدل/توكيد |
| L09 | كان الطالبُ مجتهدًا | 3 | 1 | نواسخ (كان/إنّ) والخبر جملة |
| L10 | لا تُهملْ دروسَكَ | 3 | 2 | أساليب الطلب: أمر/نهي/استفهام/تمني |
| L11 | اجتهدْ طلبًا للتفوقِ | 4 | 2 | مفعول مطلق/لأجله/معه |
| L12 | اشتريتُ عشرينَ كتابًا | 3 | 1 | عدد + تمييز، والحال |
| L13 | الطلابُ يكتبونَ الدرسَ | 3 | 1 | علامات: مثنى/أفعال خمسة/جمع سالم |
| L14 | إذا جاءَ المسلمُ فأكرمْهُ | 5 | 3 | شرط، نداء، استثناء |
| L15 | الطالبُ المجتهدُ يقرأُ كتابَ العلمِ في المسجدِ كلَّ يومٍ | 9 | 4 | كل شيء معًا |

Each level in `curriculum.json` carries: its Ajurrumiyyah bāb, the awāmil introduced (with what they govern), the corpus sentences to tarkeeb, inline annotated examples for patterns not yet in the parser, and practice tasks for the student.

## Extending the data

1. **New words** → add entries to `lexicon.json` (bare key, no diacritics; verbs list `madi/mudari/amr`; adjectives use `"kind": "sifa"`).
2. **New sentences** → add a record to `sentences.json` following the schema in its `meta.word_fields`, then run `validate` and `test`.
3. **Human collection** → fill `templates/collection_template.csv` (one row per word: sentence id, word, class, case, mahall, sign, full i'rab). Its columns mirror the JSON model, so rows convert 1:1 into `words[]` records.

## Scope & limits

- The parser is a deterministic, lexicon-driven rule engine — it reliably handles
  the structures covered by the corpus (nominal/verbal sentences, كان/إنّ group,
  جار ومجرور, نعت, عطف, شرط, استثناء, نداء, نهي/أمر, استفهام, pronoun suffixes).
  Unknown words fall back to case-hints from their diacritics; it is **not** a
  full morphological analyzer (no root/pattern mining, no full conjugation).
- All fixed vocabularies (position ids, purpose categories) are validated for
  cross-file consistency by `tarkeeb.py validate`.
