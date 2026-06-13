import streamlit as st
import pandas as pd
import re
from collections import Counter

from googleapiclient.discovery import build

import plotly.express as px

from wordcloud import WordCloud
import matplotlib.pyplot as plt

from konlpy.tag import Okt


st.set_page_config(
    page_title="유튜브 댓글 분석기",
    page_icon="🎥",
    layout="wide"
)

st.title("🎥 유튜브 댓글 심층 분석기")

# -------------------
# API KEY
# -------------------

api_key = st.sidebar.text_input(
    "YouTube API Key",
    type="password"
)

# -------------------
# URL 입력
# -------------------

url = st.text_input(
    "유튜브 링크 입력",
    placeholder="https://www.youtube.com/watch?v=..."
)


# -------------------
# Video ID 추출
# -------------------

def get_video_id(url):

    patterns = [
        r"v=([^&]+)",
        r"youtu\.be/([^?]+)"
    ]

    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)

    return None


# -------------------
# 댓글 수집
# -------------------

def get_comments(video_id, api_key):

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
                "comment": snippet["textDisplay"],
                "likes": snippet["likeCount"]
            })

        request = youtube.commentThreads().list_next(
            request,
            response
        )

    return pd.DataFrame(comments)


# -------------------
# 분석
# -------------------

if st.button("분석 시작"):

    if not api_key:
        st.error("API Key를 입력하세요.")
        st.stop()

    video_id = get_video_id(url)

    if not video_id:
        st.error("올바른 유튜브 링크가 아닙니다.")
        st.stop()

    with st.spinner("댓글 수집 중..."):

        df = get_comments(video_id, api_key)

    if len(df) == 0:
        st.warning("댓글이 없습니다.")
        st.stop()

    st.success(f"{len(df):,}개의 댓글 분석 완료!")

    # -------------------
    # 기본 통계
    # -------------------

    col1, col2, col3 = st.columns(3)

    col1.metric("댓글 수", f"{len(df):,}")

    col2.metric(
        "평균 좋아요",
        round(df["likes"].mean(), 2)
    )

    col3.metric(
        "최대 좋아요",
        df["likes"].max()
    )

    # -------------------
    # 댓글 길이 분석
    # -------------------

    df["length"] = df["comment"].str.len()

    fig = px.histogram(
        df,
        x="length",
        nbins=30,
        title="댓글 길이 분포"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # -------------------
    # 형태소 분석
    # -------------------

    okt = Okt()

    stopwords = {
        "것", "수", "진짜", "너무",
        "영상", "그냥", "정말",
        "이거", "저거", "있는",
        "하는", "하고", "에서",
        "입니다", "ㅋㅋ", "ㅎㅎ"
    }

    nouns = []

    for text in df["comment"]:

        try:

            words = okt.nouns(str(text))

            for word in words:

                if len(word) >= 2 and word not in stopwords:
                    nouns.append(word)

        except:
            pass

    word_freq = Counter(nouns)

    # -------------------
    # TOP 단어
    # -------------------

    top_words = pd.DataFrame(
        word_freq.most_common(30),
        columns=["단어", "빈도"]
    )

    fig2 = px.bar(
        top_words,
        x="단어",
        y="빈도",
        title="TOP 30 키워드"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # -------------------
    # 워드클라우드
    # -------------------

    st.subheader("☁️ 워드클라우드")

    text_data = " ".join(nouns)

    font_path = "NanumGothic.ttf"

    try:

        wc = WordCloud(
            width=1200,
            height=600,
            background_color="white",
            font_path=font_path
        ).generate(text_data)

        fig3, ax = plt.subplots(
            figsize=(14, 7)
        )

        ax.imshow(wc)
        ax.axis("off")

        st.pyplot(fig3)

    except Exception:

        st.warning(
            "NanumGothic.ttf 파일을 프로젝트 폴더에 추가하세요."
        )

    # -------------------
    # 댓글 데이터
    # -------------------

    st.subheader("댓글 원본")

    st.dataframe(
        df.head(100),
        use_container_width=True
    )
