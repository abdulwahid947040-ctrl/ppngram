import re

import pandas as pd
import plotly.express as px
import streamlit as st


def verse_mask(verses, word, only_whole_word):
    """Mask of verses containing ``word``, as a whole word or as a substring."""
    if only_whole_word:
        # A whole word is delimited by spaces or by the start/end of the verse.
        pattern = r"(?:^| )" + re.escape(word) + r"(?: |$)"
        return verses["verse"].str.contains(pattern, regex=True, na=False)
    return verses["verse"].str.contains(re.escape(word), regex=True, na=False)


def sentiment_of(text, lexicon):
    words = text.replace(".", "").replace("،", "").replace("؟", "").split(" ")
    sentiment_sum = 0.0
    sentiment_count = 0.0
    for w in words:
        w = w.strip()
        if w in lexicon:
            sentiment_sum += lexicon[w]
            sentiment_count += 1
    return sentiment_sum / (sentiment_count + 1e-10)


@st.cache_data(show_spinner="در حال بارگذاری داده‌ها...")
def load_data():
    verses = pd.read_csv("verses.tsv", sep="\t").dropna()
    verses["poet_with_century"] = verses["poet"] + " از قرن " + verses["century"].astype("str")

    sentiments = pd.read_csv(
        "https://raw.githubusercontent.com/Text-Mining/Persian-Sentiment-Resources/master/PersianSWN.csv",
        sep="\t",
        header=None,
    )
    sentiments[1] = sentiments[1].apply(lambda s: str(s).split(" ")[0])
    sentiments[5] = sentiments[2] * (sentiments[3] - sentiments[4])

    sentiments = sentiments.groupby(by=[1])[5].mean()

    sentiments_map = sentiments[sentiments != 0].to_dict()
    sentiments_map = {k: v for (k, v) in sentiments_map.items() if " " not in k}

    verses["sentiment"] = verses["verse"].apply(lambda verse: sentiment_of(verse, sentiments_map))
    return verses


st.set_page_config(
    page_title="بررسی استفاده از عبارات مختلف در اشعار فارسی در طول زمان از قرن سوم هجری تا دوران معاصر",
    layout="wide",
)
st.title("بررسی استفاده از عبارات مختلف در اشعار فارسی در طول زمان از قرن سوم هجری تا دوران معاصر")
st.write('<style>div[data-testid="stRadio"] div[role="radiogroup"]{flex-direction:row;}</style>', unsafe_allow_html=True)
st.markdown(
    "همه‌ی اشعار به همت مجموعه‌ی [گنجور](https://ganjoor.net/) جمع‌آوری و از "
    "[مخزن این پروژه](https://github.com/ganjoor/ganjoor-db) برداشت شده است"
)

verses = load_data()
poets = sorted(list(set(verses["poet_with_century"])))

words_input = st.text_input(
    label="لطفاً کلمه یا کلمات مورد نظرتان را وارد کنید. کلمه‌های مختلف را با ویرگول (،) از هم جدا کنید",
    value="تلخ، شیرین",
)
poets_list = st.multiselect(label="لطفاً شاعران مورد نظرتان را انتخاب کنید", options=poets, default=poets)
verses = verses[verses["poet_with_century"].isin(poets_list)]

st.markdown(f"در مجموع {len(verses)} «مصرع» شعر از این شعرا داریم")

groupby_var = st.radio(
    label="دسته‌بندی بر اساس شاعر یا قرن؟",
    options=["century", "poet_with_century"],
    index=0,
    format_func=lambda v: "قرن" if v == "century" else "شاعر",
)
groupby_label = "قرن" if groupby_var == "century" else "شاعر"

show_sentiments = st.checkbox(label=f"نمایش حس (سنتیمنت) شعرهای هر {groupby_label}", value=False)

ngram_all = (
    verses.groupby(by=[groupby_var])["verse"].count()
    if not show_sentiments
    else verses.groupby(by=[groupby_var])["sentiment"].mean()
)

cols = st.columns([1, 1])
with cols[0]:
    only_whole_word = st.checkbox(label="کلمه فقط به شکل کامل", value=True)
with cols[1]:
    if not show_sentiments:
        compute_proportion = st.checkbox(label=f"نسبت به کل شعرهای هر {groupby_label}", value=True)

raw_words = [w.strip() for w in re.split(r"[،,]", words_input) if w.strip()]

if not raw_words:
    st.info("لطفاً حداقل یک کلمه وارد کنید تا نمودار رسم شود.")
    st.stop()

ngrams = {}
masks = {}
for w in dict.fromkeys(raw_words):
    mask = verse_mask(verses, w, only_whole_word)
    masks[w] = mask
    if show_sentiments:
        ngram = verses[mask].groupby(by=[groupby_var])["sentiment"].mean()
        ngram = ngram_all * (ngram / ngram_all)  # keep empty groups as 0 in the chart
    else:
        ngram = verses[mask].groupby(by=[groupby_var])["verse"].count()
        ngram = (100 if compute_proportion else ngram_all) * (ngram / ngram_all)  # keep empty groups as 0 in the chart
    ngrams[w] = ngram

df = pd.DataFrame(ngrams).fillna(value=0).reindex(ngram_all.index)
df[groupby_var] = ngram_all.index

word_list = list(ngrams.keys())
fig = px.bar(
    df,
    y=groupby_var,
    x=word_list,
    orientation="h",
    barmode="group",
    height=min(max(300, (1 + len(word_list)) * (200 if groupby_var == "century" else 600)), 2400),
)

fig.update_layout(
    title=f"{'حس' if show_sentiments else ('نسبت استفاده از' if compute_proportion else 'تعداد استفاده از')} کلمات مختلف در شعر فارسی در گذر زمان و بین شعرای مختلف",
    yaxis_title="قرن هجری" if groupby_var == "century" else "شاعر",
    xaxis_title=f"{'میانگین حس' if show_sentiments else ('درصد' if compute_proportion else 'تعداد')} مصراع‌های دارای کلمه‌ی مورد نظر",
    legend_title="کلمه",
    font={"family": "Tahoma, sans-serif", "size": 12, "color": "RebeccaPurple"},
)

st.plotly_chart(fig, width="stretch")

matched = pd.concat([verses[mask] for mask in masks.values()], ignore_index=True).drop_duplicates()
matched = matched.drop(columns=["poet_with_century"])

with st.spinner("در حال آماده‌سازی فایل..."):
    st.download_button(
        label="فایل حاوی شعرهایی که هر یک از کلمات بالا در آن‌ها به کار رفته را دانلود کنید",
        data=matched.to_csv(index=False, sep="\t"),
        file_name="poems.tsv",
        mime="text/tab-separated-values",
    )
