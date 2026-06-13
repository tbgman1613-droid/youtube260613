import streamlit as st
import pandas as pd
import numpy as np
import re
from collections import Counter

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from kiwipiepy import Kiwi

import plotly.express as px

from wordcloud import WordCloud
import matplotlib.pyplot as plt

# ----------------------------
# 페이지 설정
# ----------------------------

st.set_page_config(
    page_title="YouTube Comment Insight AI",
    page_icon="🎥",
    layout="wide"
)

st.title("🎥 YouTube Comment Insight AI")

# ----------------------------
# API KEY
# ----------------------------

try:
    api_key = st.secrets["YOUTUBE_API_KEY"]
except:
    st.error("Secrets에 YOUTUBE_API_KEY를 등록하세요.")
    st.stop()

# ----------------------------
# 유튜브 URL
# ----------------------------

url = st.text_input(
    "유튜브 링크 입력",
    placeholder="https://www.youtube.com/watch?v=..."
)

# ----------------------------
# Video ID 추출
# ----------------------------

def get_video_id(url):

    patterns = [
        r"v=([^&]+)",
        r"youtu\.be/([^?]+)",
        r"shorts/([^?]+)"
    ]

    for p in patterns:
        m = re.search(p, url)

        if m:
            return m.group(1)

    return None


# ----------------------------
# 영상 정보
# ----------------------------

def get_video_info(video_id):

    youtube = build(
        "youtube",
        "v3",
        developerKey=api_key
    )

    response = youtube.videos().list(
        part="snippet,statistics",
        id=video_id
    ).execute()

    if not response["items"]:
        return None

    item = response["items"][0]

    return {
        "title": item["snippet"]["title"],
        "channel": item["snippet"]["channelTitle"],
        "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
        "views": int(item["statistics"].get("viewCount", 0))
    }


# ----------------------------
# 댓글 수집
# ----------------------------

def get_comments(video_id):

    youtube = build(
        "youtube",
        "v3",
        developerKey=api_key
    )

    comments = []

    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,
        textFormat="plainText"
    )

    while request:

        response = request.execute()

        for item in response["items"]:

            snippet = item["snippet"]["topLevelComment"]["snippet"]

            comments.append({
                "댓글": snippet["textDisplay"],
                "좋아요": snippet["likeCount"]
            })

        request = youtube.commentThreads().list_next(
            request,
            response
        )

    return pd.DataFrame(comments)


# ----------------------------
# 형태소 분석
# ----------------------------

def extract_keywords(texts):

    kiwi = Kiwi()

    stopwords = {
        "진짜","정말","너무","그냥","이거",
        "저거","영상","사람","오늘","생각",
        "대한","때문","입니다","있어요"
    }

    words = []

    for text in texts:

        try:

            result = kiwi.tokenize(str(text))

            for token in result:

                if token.tag.startswith("NN"):  # 명사

                    word = token.form

                    if len(word) >= 2 and word not in stopwords:
                        words.append(word)

        except:
            pass

    return Counter(words)


# ----------------------------
# 분석 시작
# ----------------------------

if st.button("🚀 분석 시작"):

    if not url:
        st.warning("유튜브 링크를 입력하세요.")
        st.stop()

    video_id = get_video_id(url)

    if not video_id:
        st.error("유효한 유튜브 링크가 아닙니다.")
        st.stop()

    try:

        with st.spinner("영상 정보 불러오는 중..."):
            info = get_video_info(video_id)

        with st.spinner("댓글 수집 중..."):
            df = get_comments(video_id)

    except HttpError as e:

        if "API key not valid" in str(e):
            st.error("YouTube API Key가 올바르지 않습니다.")
        else:
            st.error(str(e))

        st.stop()

    if len(df) == 0:
        st.warning("댓글이 없습니다.")
        st.stop()

    # ------------------------
    # 헤더
    # ------------------------

    col1, col2 = st.columns([1, 2])

    with col1:
        st.image(info["thumbnail"])

    with col2:
        st.subheader(info["title"])
        st.write(f"📺 {info['channel']}")
        st.write(f"👀 {info['views']:,} 조회수")

    st.divider()

    # ------------------------
    # KPI
    # ------------------------

    col1, col2, col3 = st.columns(3)

    col1.metric("💬 댓글 수", f"{len(df):,}")
    col2.metric("👍 평균 좋아요", round(df["좋아요"].mean(), 2))
    col3.metric("🔥 최고 좋아요", int(df["좋아요"].max()))

    st.divider()

    # ------------------------
    # 키워드 분석
    # ------------------------

    counter = extract_keywords(df["댓글"])

    top_words = counter.most_common(10)

    if top_words:

        st.subheader("🤖 AI 인사이트")

        st.success(
            f"""
            시청자들이 가장 많이 언급한 키워드는
            **'{top_words[0][0]}'** 입니다.

            댓글에서는 {', '.join([w for w, c in top_words[:5]])}
            관련 언급이 특히 많이 나타났습니다.
            """
        )

    # ------------------------
    # TOP 키워드 카드
    # ------------------------

    st.subheader("🔥 핵심 키워드")

    cols = st.columns(5)

    for col, (word, count) in zip(cols, top_words[:5]):

        col.metric(word, count)

    # ------------------------
    # 워드클라우드
    # ------------------------

    st.subheader("☁️ 워드클라우드")

    try:

        wc = WordCloud(
            font_path="NanumGothic.ttf",
            width=2000,
            height=1000,
            background_color="white"
        ).generate_from_frequencies(counter)

        fig, ax = plt.subplots(figsize=(16, 8))

        ax.imshow(wc)
        ax.axis("off")

        st.pyplot(fig)

    except Exception:
        st.warning(
            "프로젝트 폴더에 NanumGothic.ttf를 추가하세요."
        )

    # ------------------------
    # TOP 20 키워드 그래프
    # ------------------------

    st.subheader("📊 TOP 20 키워드")

    top20 = pd.DataFrame(
        counter.most_common(20),
        columns=["단어", "빈도"]
    )

    fig = px.bar(
        top20,
        x="단어",
        y="빈도",
        title="댓글 키워드 순위"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ------------------------
    # 인기 댓글
    # ------------------------

    st.subheader("👍 인기 댓글 TOP 5")

    top_comments = (
        df
        .sort_values(
            "좋아요",
            ascending=False
        )
        .head(5)
    )

    for _, row in top_comments.iterrows():

        st.info(
            f"👍 {row['좋아요']} 좋아요\n\n{row['댓글']}"
        )

    # ------------------------
    # 댓글 길이 분석
    # ------------------------

    st.subheader("📈 댓글 길이 분석")

    df["길이"] = df["댓글"].astype(str).str.len()

    fig2 = px.histogram(
        df,
        x="길이",
        nbins=30
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # ------------------------
    # 원본 댓글
    # ------------------------

    st.subheader("💬 전체 댓글")

    keyword = st.text_input("댓글 검색")

    if keyword:

        filtered = df[
            df["댓글"]
            .str.contains(
                keyword,
                case=False,
                na=False
            )
        ]

        st.dataframe(
            filtered,
            use_container_width=True
        )

    else:

        st.dataframe(
            df,
            use_container_width=True
        )
