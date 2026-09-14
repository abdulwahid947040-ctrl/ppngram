# نحو کا ڈیٹا سیٹ — اردو رہنما

یہ فولڈر پورے ڈیٹا سیٹ کا **آسان اردو خلاصہ** ہے:

- **rahnuma.md** — مکمل رہنما: چھ سوال، بنیادی تصورات، ۱۵ علامتیں، ۱۰ تمثیلات، ۶ مراحل، ۲۸ قواعد کے ادلہ، مشق کا طریقہ

باقی سب عربی/انگریزی میں اوپر والے فولڈر (`nahw/`) میں ہے:
- نصاب: `curriculum.json` — موضوعات: `topics/` — قواعد: `rules.json` — عوامل: `awamil.json`
- آلہ: `tarkeeb.py` (parse, quiz, test, roadmap, awamil, rules)
- قرآن و حدیث لانے کے لیے: `fetch_examples.py`

**شروع کرنے کے تین کمانڈ:**
```bash
python3 nahw/tarkeeb.py roadmap   # خریطۂ راہ
python3 nahw/tarkeeb.py quiz      # مشق
python3 nahw/tarkeeb.py parse "الطالبُ يقرأُ الكتابَ"
```
