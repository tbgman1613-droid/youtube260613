import streamlit as st
import pandas as pd
import re
from collections import Counter

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import plotly.express as px

from wordcloud import WordCloud
import matplotlib.pyplot as plt


# ------------------
# 페이지 설정
# ------------------

st.set_page_config(
    page_title="YouTube 댓글 분석기",
    page_icon="🎥",
    layout="wide"
)

st.title("🎥 YouTube 댓글 심층 분석기")

# ------------------
# API KEY
# ------------------

try:
    api_key = st.secrets["YOUTUBE_API_KEY"]
except:
    st.error("Secrets에 YOUTUBE_API_KEY를 등록하세요.")
    st.stop()

# ------------------
# URL 입력
# ------------------

url = st.text_input(
    "유튜브 링크 입력",
    placeholder="https://www.youtube.com/watch?v=..."
)

# ------------------
# Video ID 추출
# ------------------

def get_video_id(url):

    patterns = [
        r"v=([^&]+)",
        r"youtu\.be/([^?]+)",
        r"shorts/([^?]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)

        if match:
            return match.group(1)

    return None

# ------------------
# 댓글 수집
# ------------------

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

        try:
            response = request.execute()

        except HttpError as e:

            error_text = str(e)

            if "commentsDisabled" in error_text:
                st.error("댓글이 비활성화된 영상입니다.")
            elif "quotaExceeded" in error_text:
                st.error("YouTube API 할당량을 초과했습니다.")
            elif "API key not valid" in error_text:
                st.error("API Key가 올바르지 않습니다.")
            else:
                st.error(error_text)

            return pd.DataFrame()

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

# ------------------
# 분석 시작
# ------------------

if st.button("분석 시작"):

    if not url:
        st.warning("유튜브 링크를 입력하세요.")
        st.stop()

    video_id = get_video_id(url)

    if not video_id:
        st.error("올바른 유튜브 링크가 아닙니다.")
        st.stop()

    with st.spinner("댓글 수집 중..."):

        df = get_comments(video_id)

    if len(df) == 0:
        st.stop()

    st.success(f"{len(df):,}개의 댓글 분석 완료!")

    # ------------------
    # 통계
    # ------------------

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "댓글 수",
        f"{len(df):,}"
    )

    col2.metric(
        "평균 좋아요",
        round(df["좋아요"].mean(), 2)
    )

    col3.metric(
        "최대 좋아요",
        df["좋아요"].max()
    )

    # ------------------
    # 댓글 길이
    # ------------------

    df["댓글길이"] = df["댓글"].astype(str).str.len()

    fig = px.histogram(
        df,
        x="댓글길이",
        nbins=30,
        title="댓글 길이 분포"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ------------------
    # 키워드 추출
    # ------------------

    text = " ".join(df["댓글"].astype(str))

    words = re.findall(
        r"[가-힣]{2,}",
        text
    )

    stopwords = {
        "진짜","정말","너무","그냥",
        "이거","저거","영상","사람",
        "때문","오늘","이제","계속",
        "생각","우리","여기","저기",
        "대한","입니다","있어요"
    }

    filtered_words = [
        w for w in words
        if w not in stopwords
    ]

    counter = Counter(filtered_words)

    # ------------------
    # TOP30
    # ------------------

    top30 = pd.DataFrame(
        counter.most_common(30),
        columns=["단어","빈도"]
    )

    st.subheader("🔥 TOP 30 키워드")

    fig2 = px.bar(
        top30,
        x="단어",
        y="빈도"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # ------------------
    # 워드클라우드
    # ------------------

    st.subheader("☁️ 워드클라우드")

    try:

        wc = WordCloud(
            font_path="NanumGothic.ttf",
            width=1400,
            height=700,
            background_color="white"
        ).generate(
            " ".join(filtered_words)
        )

        fig3, ax = plt.subplots(
            figsize=(14,7)
        )

        ax.imshow(wc)
        ax.axis("off")

        st.pyplot(fig3)

    except Exception as e:

        st.error(
            f"폰트 오류: {e}"
        )

    # ------------------
    # 원본 댓글
    # ------------------

    st.subheader("댓글 데이터")

    st.dataframe(
        df,
        use_container_width=True
    )
