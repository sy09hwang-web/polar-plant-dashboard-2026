import io
import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─────────────────────────────────────────────
# 페이지 설정 및 한글 폰트 CSS
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="인천아라고등학교 생육·환경 분석 대시보드",
    page_icon="🌱",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
   font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 필수 2: 열 이름 표준화 함수
# ─────────────────────────────────────────────
def std_cols(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    rename = {}
    for c in df.columns:
        k = c.lower().replace(" ", "")
        if k in ("time", "categories", "시간", "날짜", "datetime", "date"):
            rename[c] = "time"
        elif k in ("temperature", "온도"):
            rename[c] = "temperature"
        elif k in ("humidity", "습도"):
            rename[c] = "humidity"
        elif k == "ph":
            rename[c] = "ph"
        elif k == "ec":
            rename[c] = "ec"
        elif "수온" in k or "watertemp" in k:
            rename[c] = "수온"
        elif "co2" in k or "이산화탄소" in k:
            rename[c] = "CO2"
        elif "생중량" in k:
            rename[c] = "생중량"
        elif "잎" in k:
            rename[c] = "잎 수"
        elif "지상부" in k and "길이" in k:
            rename[c] = "지상부 길이"
        elif "지하부" in k and "길이" in k:
            rename[c] = "지하부 길이"
        elif "지상부" in k and ("질량" in k or "무게" in k):
            rename[c] = "지상부 질량"
        elif "지하부" in k and ("질량" in k or "무게" in k):
            rename[c] = "지하부 질량"
        elif "개체" in k:
            rename[c] = "개체번호"
    df = df.rename(columns=rename)
    for c in df.columns:
        if c in ("time", "개체번호"):
            continue
        if not pd.api.types.is_numeric_dtype(df[c]):
            num = pd.to_numeric(
                df[c].astype(str).str.replace(",", "").
                str.extract(r"(-?\d+\.?\d*)")[0],
                errors="coerce"
            )
            if num.notna().mean() >= 0.5:
                df[c] = num
    if "생중량" not in df.columns and {"지상부 질량", "지하부 질량"} <= set(df.columns):
        df["생중량"] = df["지상부 질량"] + df["지하부 질량"]
    if "time" in df.columns:
        t = df["time"].astype(str).str.strip()
        parsed = pd.to_datetime(t, errors="coerce", format="mixed")
        bad = parsed.isna() & t.str.match(r"^\d{8}_\d{1,2}$")
        if bad.any():
            parts = t[bad].str.split("_", expand=True)
            parsed[bad] = pd.to_datetime(parts[0], format="%Y%m%d") + \
                         pd.to_timedelta(parts[1].astype(int), unit="h")
        df["time"] = parsed
    return df

# ─────────────────────────────────────────────
# 파일 읽기 함수 (CSV 및 Excel 지원)
# ─────────────────────────────────────────────
def read_data_file(file):
    name = file.name.lower()
    data = file.getvalue()
    try:
        if name.endswith('.xlsx') or name.endswith('.xls'):
            return pd.read_excel(io.BytesIO(data))
        else:
            for enc in ("utf-8-sig", "cp949"):
                try:
                    return pd.read_csv(io.BytesIO(data), encoding=enc)
                except Exception:
                    pass
    except Exception as e:
        st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
    return pd.DataFrame()

# ─────────────────────────────────────────────
# 학교명 추출 (파일명 앞부분)
# ─────────────────────────────────────────────
def extract_school_name(filename):
    base = os.path.basename(filename)
    name = base.rsplit(".", 1)[0]
    parts = name.replace("_", " ").replace("-", " ").split()
    return parts[0] if parts else name

# ─────────────────────────────────────────────
# Plotly 폰트 설정 헬퍼
# ─────────────────────────────────────────────
def set_fig_font(fig):
    fig.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))

# ─────────────────────────────────────────────
# 사이드바: 파일 업로드
# ─────────────────────────────────────────────
st.sidebar.title("📁 데이터 업로드")

env_file = st.sidebar.file_uploader("환경 데이터 파일 (CSV 또는 Excel)", type=["csv", "xlsx", "xls"])
growth_file = st.sidebar.file_uploader("생육 데이터 파일 (CSV 또는 Excel)", type=["csv", "xlsx", "xls"])

# 파일이 없으면 안내 메시지 출력 후 중단
if env_file is None and growth_file is None:
    st.info("왼쪽 사이드바에서 인천아라고등학교 환경 및 생육 데이터 파일을 업로드해 주세요.")
    st.stop()

env_df = None
growth_df = None

if env_file is not None:
    with st.spinner("환경 데이터를 읽는 중..."):
        raw_env = read_data_file(env_file)
        if not raw_env.empty:
            env_df = std_cols(raw_env)

if growth_file is not None:
    with st.spinner("생육 데이터를 읽는 중..."):
        raw_growth = read_data_file(growth_file)
        if not raw_growth.empty:
            growth_df = std_cols(raw_growth)

# 학교명 추출 및 표시
school_name = None
if env_file is not None:
    school_name = extract_school_name(env_file.name)
elif growth_file is not None:
    school_name = extract_school_name(growth_file.name)

if school_name:
    st.sidebar.success(f"불러온 학교: {school_name}")

# ─────────────────────────────────────────────
# 메인 화면 제목
# ─────────────────────────────────────────────
st.title(f"🌱 {school_name or '인천아라고등학교'} 생육·환경 분석 대시보드")

# ─────────────────────────────────────────────
# 탭 구성
# ─────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 환경 데이터", "🌿 생육 데이터", "🔗 종합 분석"])

# ─────────────────────────────────────────────
# 탭 1: 환경 데이터
# ─────────────────────────────────────────────
with tab1:
    try:
        if env_df is None or env_df.empty:
            st.info("환경 데이터가 업로드되지 않았거나 데이터가 없습니다.")
        else:
            if "time" in env_df.columns and env_df["time"].notna().any():
                t_min = env_df["time"].min()
                t_max = env_df["time"].max()
                st.caption(f"📅 데이터 기간: {t_min.strftime('%Y-%m-%d %H:%M')} ~ {t_max.strftime('%Y-%m-%d %H:%M')}")

            # 환경 지표 요약 카드
            available_env_metrics = [c for c in ["temperature", "humidity", "ph", "ec", "수온", "CO2"] if c in env_df.columns]
            metric_cols = st.columns(min(len(available_env_metrics), 4) if available_env_metrics else 1)
            
            labels_map = {
                "temperature": "온도 (℃)",
                "humidity": "습도 (%)",
                "ph": "pH",
                "ec": "EC (mS/cm)",
                "수온": "수온 (℃)",
                "CO2": "CO2 (ppm)"
            }
            
            for i, key in enumerate(available_env_metrics[:4]):
                vals = env_df[key].dropna()
                with metric_cols[i]:
                    if len(vals) >= 2:
                        st.metric(labels_map.get(key, key), f"{vals.mean():.1f}")
                    else:
                        st.metric(labels_map.get(key, key), "데이터 부족")

            st.divider()

            # 환경 시계열 서브플롯
            if available_env_metrics:
                n = len(available_env_metrics)
                fig_env = make_subplots(
                    rows=n, cols=1,
                    subplot_titles=[labels_map.get(c, c) for c in available_env_metrics],
                    vertical_spacing=0.06
                )
                for i, col in enumerate(available_env_metrics, 1):
                    plot_df = env_df[["time", col]].dropna()
                    if len(plot_df) >= 2:
                        fig_env.add_trace(
                            go.Scatter(
                                x=plot_df["time"],
                                y=plot_df
