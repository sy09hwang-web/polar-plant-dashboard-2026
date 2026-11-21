import io
import os
import zipfile
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from plotly.subplots import make_subplots

st.set_page_config(
    page_title="미생물 실험 생육 분석",
    page_icon="🌱",
    layout="wide"
)

# ─────────────────────────────────────
# 디자인
# ─────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');

html, body, [class*="css"], [class*="st-"] {
    font-family: 'Noto Sans KR', sans-serif;
}

.block-container {
    padding-top: 1.8rem;
}

[data-testid="stMetric"] {
    background-color: #f4f8f4;
    padding: 16px;
    border-radius: 12px;
    border: 1px solid #e2ebe2;
}

h1, h2, h3 {
    color: #244b36;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────
# 데이터 처리 함수
# ─────────────────────────────────────
def standardize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    rename = {}

    for col in df.columns:
        key = col.lower().replace(" ", "").replace("_", "")

        if key in ["time", "시간", "날짜", "date", "datetime", "측정시간"]:
            rename[col] = "time"

        elif key in ["temperature", "온도", "기온"]:
            rename[col] = "temperature"

        elif key in ["humidity", "습도"]:
            rename[col] = "humidity"

        elif key in ["ph"]:
            rename[col] = "ph"

        elif key in ["ec"]:
            rename[col] = "ec"

        elif "개체번호" in key or key in ["id", "individual"]:
            rename[col] = "개체번호"

        elif "잎수" in key:
            rename[col] = "잎 수"

        elif "지상부" in key and "길이" in key:
            rename[col] = "지상부 길이"

        elif "지하부" in key and "길이" in key:
            rename[col] = "지하부 길이"

        elif "지상부" in key and ("질량" in key or "무게" in key):
            rename[col] = "지상부 질량"

        elif "지하부" in key and ("질량" in key or "무게" in key):
            rename[col] = "지하부 질량"

        elif "생중량" in key:
            rename[col] = "생중량"

    df = df.rename(columns=rename)

    # 숫자 데이터 변환
    for col in df.columns:
        if col not in ["time", "개체번호"]:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce"
            )

    # 생중량 계산
    if (
        "생중량" not in df.columns
        and "지상부 질량" in df.columns
        and "지하부 질량" in df.columns
    ):
        df["생중량"] = df["지상부 질량"] + df["지하부 질량"]

    # 날짜 변환
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")

    return df


def read_csv_auto(file):
    data = file.getvalue()

    for encoding in ["utf-8-sig", "cp949", "utf-8"]:
        try:
            return pd.read_csv(io.BytesIO(data), encoding=encoding)
        except Exception:
            continue

    return pd.DataFrame()


def read_excel_auto(file):
    try:
        return pd.read_excel(file)
    except Exception:
        return pd.DataFrame()


def numeric_columns(df):
    return [
        col for col in df.columns
        if pd.api.types.is_numeric_dtype(df[col])
    ]


def safe_mean(series):
    series = pd.to_numeric(series, errors="coerce").dropna()
    if len(series) == 0:
        return None
    return series.mean()


def show_metrics(df, columns):
    available = [c for c in columns if c in df.columns]

    if not available:
        st.info("표시할 수 있는 분석 데이터가 없습니다.")
        return

    cols = st.columns(min(len(available), 4))

    for i, name in enumerate(available[:4]):
        value = safe_mean(df[name])

        if value is not None:
            cols[i].metric(
                name,
                f"{value:.2f}",
                help="전체 데이터 평균"
            )
        else:
            cols[i].metric(name, "데이터 부족")


# ─────────────────────────────────────
# 사이드바 파일 업로드
# ─────────────────────────────────────
st.sidebar.title("📁 데이터 업로드")

env_file = st.sidebar.file_uploader(
    "환경 데이터 파일",
    type=["csv", "xlsx", "xls"],
    key="env"
)

growth_file = st.sidebar.file_uploader(
    "생육 데이터 파일",
    type=["csv", "xlsx", "xls"],
    key="growth"
)


def load_file(file):
    if file is None:
        return None

    ext = os.path.splitext(file.name)[1].lower()

    try:
        if ext == ".csv":
            return read_csv_auto(file)

        elif ext in [".xlsx", ".xls"]:
            return pd.read_excel(file)

    except Exception as e:
        st.error(f"{file.name} 파일 읽기 오류: {e}")

    return None


env_raw = load_file(env_file)
growth_raw = load_file(growth_file)

env_df = standardize_columns(env_raw) if env_raw is not None else None
growth_df = standardize_columns(growth_raw) if growth_raw is not None else None


# ─────────────────────────────────────
# 제목
# ─────────────────────────────────────
st.title("🌱 미생물 처리 실험 데이터 분석")
st.caption("환경 조건 및 식물 생육 데이터 기반 분석 대시보드")

st.divider()


# ─────────────────────────────────────
# 탭
# ─────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "📊 환경 데이터",
    "🌿 생육 데이터",
    "🔗 종합 분석"
])


# ═════════════════════════════════════
# TAB 1 환경 데이터
# ═════════════════════════════════════
with tab1:

    st.header("환경 데이터 분석")

    if env_df is None or env_df.empty:
        st.info("사이드바에서 환경 데이터 파일을 업로드해 주세요.")

    else:

        env_metrics = [
            ("temperature", "온도 (℃)"),
            ("humidity", "습도 (%)"),
            ("ph", "pH"),
            ("ec", "EC")
        ]

        available_metrics = [
            key for key, label in env_metrics
            if key in env_df.columns
        ]

        metric_cols = st.columns(4)

        for i, (key, label) in enumerate(env_metrics):
            if key in env_df.columns:
                mean_value = safe_mean(env_df[key])

                if mean_value is not None:
                    metric_cols[i].metric(
                        label,
                        f"{mean_value:.2f}"
                    )
                else:
                    metric_cols[i].metric(label, "데이터 부족")

            else:
                metric_cols[i].metric(label, "–")

        st.divider()

        # 환경 데이터 변화 그래프
        if "time" in env_df.columns and available_metrics:

            chart_df = env_df.dropna(subset=["time"]).sort_values("time")

            for key in available_metrics:

                fig = go.Figure()

                valid = chart_df[["time", key]].dropna()

                fig.add_trace(go.Scatter(
                    x=valid["time"],
                    y=valid[key],
                    mode="lines+markers",
                    name=key,
                    line=dict(width=2)
                ))

                if len(valid) >= 2:
                    x = np.arange(len(valid))
                    y = valid[key].values

                    slope, intercept = np.polyfit(x, y, 1)

                    fig.add_trace(go.Scatter(
                        x=valid["time"],
                        y=slope * x + intercept,
                        mode="lines",
                        name="추세선",
                        line=dict(dash="dash")
                    ))

                fig.update_layout(
                    title=f"{key} 변화 추이",
                    xaxis_title="측정 시간",
                    yaxis_title=key,
                    height=350,
                    hovermode="x unified"
                )

                st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("시간 데이터가 없거나 분석할 환경 지표가 부족합니다.")

        # 환경 통계
        st.subheader("환경 데이터 통계")

        valid_numeric = numeric_columns(env_df)

        if valid_numeric:
            st.dataframe(
                env_df[valid_numeric].describe().round(2),
                use_container_width=True
            )

        # 원본 데이터
        st.subheader("환경 원본 데이터")

        st.dataframe(
            env_df,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "📥 환경 데이터 다운로드",
            env_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="환경데이터.csv",
            mime="text/csv"
        )


# ═════════════════════════════════════
# TAB 2 생육 데이터
# ═════════════════════════════════════
with tab2:

    st.header("생육 데이터 분석")

    if growth_df is None or growth_df.empty:
        st.info("사이드바에서 생육 데이터 파일을 업로드해 주세요.")

    else:

        growth_metrics = [
            "잎 수",
            "지상부 길이",
            "지하부 길이",
            "지상부 질량",
            "지하부 질량",
            "생중량"
        ]

        available_growth = [
            c for c in growth_metrics
            if c in growth_df.columns
        ]

        show_metrics(growth_df, available_growth)

        st.divider()

        # 개체별 생중량
        if "개체번호" in growth_df.columns and "생중량" in growth_df.columns:

            weight_df = growth_df[["개체번호", "생중량"]].dropna()

            if not weight_df.empty:

                weight_df = weight_df.sort_values(
                    "생중량",
                    ascending=False
                )

                fig = px.bar(
                    weight_df,
                    x="개체번호",
                    y="생중량",
                    color="생중량",
                    color_continuous_scale="Greens",
                    title="개체별 생중량 비교"
                )

                fig.update_layout(height=450)

                st.plotly_chart(fig, use_container_width=True)

                st.subheader("생중량 상위 5개 개체")

                st.dataframe(
                    weight_df.head(5),
                    use_container_width=True,
                    hide_index=True
                )

                st.subheader("생중량 하위 5개 개체")

                st.dataframe(
                    weight_df.tail(5).sort_values("생중량"),
                    use_container_width=True,
                    hide_index=True
                )

        st.divider()

        # 산점도
        scatter_pairs = [
            ("잎 수", "지상부 길이"),
            ("잎 수", "생중량"),
            ("지상부 길이", "생중량"),
            ("지하부 길이", "생중량")
        ]

        for x, y in scatter_pairs:

            if x in growth_df.columns and y in growth_df.columns:

                data = growth_df[[x, y]].dropna()

                if len(data) >= 2:

                    corr = data[x].corr(data[y])

                    fig = px.scatter(
                        data,
                        x=x,
                        y=y,
                        trendline="ols",
                        title=f"{x}와 {y}의 관계 (r={corr:.2f})"
                    )

                    fig.update_layout(height=380)

                    st.plotly_chart(fig, use_container_width=True)

        # 통계
        st.subheader("생육 지표 통계")

        if available_growth:
            st.dataframe(
                growth_df[available_growth].describe().round(2),
                use_container_width=True
            )

        # 전체 데이터
        st.subheader("생육 데이터 원본")

        st.dataframe(
            growth_df,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "📥 생육 데이터 다운로드",
            growth_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="생육데이터.csv",
            mime="text/csv"
        )


# ═════════════════════════════════════
# TAB 3 종합 분석
# ═════════════════════════════════════
with tab3:

    st.header("환경-생육 종합 분석")

    if env_df is None or growth_df is None:
        st.info("환경 데이터와 생육 데이터를 모두 업로드해야 종합 분석이 가능합니다.")

    else:

        st.subheader("생육 지표 간 상관관계")

        growth_numeric = [
            c for c in growth_metrics
            if c in growth_df.columns
        ]

        if len(growth_numeric) >= 2:

            corr = growth_df[growth_numeric].corr()

            fig = px.imshow(
                corr,
                text_auto=".2f",
                color_continuous_scale="RdYlGn",
                title="생육 지표 상관관계",
                aspect="auto"
            )

            fig.update_layout(height=550)

            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # 환경 데이터 일별 평균
        if "time" in env_df.columns:

            env_valid = env_df.dropna(subset=["time"]).copy()

            env_valid["날짜"] = env_valid["time"].dt.date

            daily_cols = [
                c for c in ["temperature", "humidity", "ph", "ec"]
                if c in env_valid.columns
            ]

            if daily_cols:

                daily = env_valid.groupby("날짜")[daily_cols].mean().reset_index()

                st.subheader("일별 환경 변화")

                for col in daily_cols:

                    fig = px.line(
                        daily,
                        x="날짜",
                        y=col,
                        markers=True,
                        title=f"일별 평균 {col} 변화"
                    )

                    st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # 생육 요약
        st.subheader("생육 데이터 요약")

        if growth_numeric:

            summary = growth_df[growth_numeric].describe().round(2)

            st.dataframe(
                summary,
                use_container_width=True
            )

        st.info("""
        분석 시 주의사항

        - 상관관계는 인과관계를 의미하지 않습니다.
        - 환경 데이터와 생육 데이터의 측정 시점이 다를 수 있습니다.
        - 실제 데이터에 기반한 결과만 해석해야 합니다.
        - 표본 수와 결측값에 따라 분석의 신뢰도가 달라질 수 있습니다.
        """)
