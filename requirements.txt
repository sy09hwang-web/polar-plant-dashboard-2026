import io
import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─────────────────────────────────────────────
# 필수 7: 한글 폰트 CSS
# ─────────────────────────────────────────────
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
# CSV 읽기 함수 (utf-8-sig → cp949 폴백)
# ─────────────────────────────────────────────
def read_csv_file(file):
    data = file.getvalue()
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(io.BytesIO(data), encoding=enc)
        except Exception:
            pass
    return pd.DataFrame()

# ─────────────────────────────────────────────
# 학교명 추출 (파일명 앞부분)
# ─────────────────────────────────────────────
def extract_school_name(filename):
    base = os.path.basename(filename)
    # 확장자 제거 후 공백/특수문자로 자른 첫 부분
    name = base.rsplit(".", 1)[0]
    # '_', '-', ' ' 기준으로 분할해 첫 토큰 사용
    parts = name.replace("_", " ").replace("-", " ").split()
    return parts[0] if parts else name

# ─────────────────────────────────────────────
# 공통: Plotly 폰트 설정 헬퍼
# ─────────────────────────────────────────────
def set_fig_font(fig):
    fig.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))

# ─────────────────────────────────────────────
# 사이드바: 파일 업로드
# ─────────────────────────────────────────────
st.sidebar.title("📁 CSV 업로드")

env_file = st.sidebar.file_uploader("환경 CSV", type="csv")
growth_file = st.sidebar.file_uploader("생육 CSV", type="csv")

# 파일이 없으면 안내
if env_file is None and growth_file is None:
    st.info("왼쪽 사이드바에서 환경 CSV와 생육 CSV를 업로드해 주세요.")
    st.stop()

env_df = None
growth_df = None

if env_file is not None:
    with st.spinner("환경 CSV를 읽는 중..."):
        raw_env = read_csv_file(env_file)
        if not raw_env.empty:
            env_df = std_cols(raw_env)

if growth_file is not None:
    with st.spinner("생육 CSV를 읽는 중..."):
        raw_growth = read_csv_file(growth_file)
        if not raw_growth.empty:
            growth_df = std_cols(raw_growth)

# 학교명 표시
school_name = None
if env_file is not None:
    school_name = extract_school_name(env_file.name)
elif growth_file is not None:
    school_name = extract_school_name(growth_file.name)

if school_name:
    st.sidebar.success(f"불러온 학교: {school_name}")

# ─────────────────────────────────────────────
# 메인 화면
# ─────────────────────────────────────────────
st.title(f"🌱 {school_name or '데이터'} 생육·환경 분석 대시보드")

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
            st.info("환경 CSV가 업로드되지 않았거나 데이터가 없습니다.")
        else:
            # 날짜 범위 안내
            if "time" in env_df.columns and env_df["time"].notna().any():
                t_min = env_df["time"].min()
                t_max = env_df["time"].max()
                st.caption(f"📅 데이터 기간: {t_min.strftime('%Y-%m-%d %H:%M')} ~ {t_max.strftime('%Y-%m-%d %H:%M')}")

            # ── 환경 지표 요약 카드 ──
            metric_cols = st.columns(4)
            env_metric_items = [
                ("temperature", "온도 (℃)"),
                ("humidity", "습도 (%)"),
                ("ph", "pH"),
                ("ec", "EC (mS/cm)"),
            ]
            for col, (key, label) in zip(metric_cols, env_metric_items):
                if key in env_df.columns:
                    vals = env_df[key].dropna()
                    if len(vals) >= 2:
                        col.metric(label, f"{vals.mean():.1f}", delta=None)
                    else:
                        col.metric(label, "데이터 부족")
                else:
                    col.metric(label, "–")

            st.divider()

            # ── 환경 시계열 서브플롯 ──
            env_cols = [c for c in ["temperature", "humidity", "ph", "ec"] if c in env_df.columns]
            if env_cols:
                n = len(env_cols)
                fig_env = make_subplots(
                    rows=n, cols=1,
                    subplot_titles=[f"{c}" for c in env_cols],
                    vertical_spacing=0.08
                )
                for i, col in enumerate(env_cols, 1):
                    plot_df = env_df[["time", col]].dropna()
                    if len(plot_df) >= 2:
                        fig_env.add_trace(
                            go.Scatter(
                                x=plot_df["time"],
                                y=plot_df[col],
                                mode="lines",
                                name=col,
                                line=dict(color="royalblue", width=1.2)
                            ),
                            row=i, col=1
                        )
                        # 추세선 (np.polyfit)
                        x_num = (plot_df["time"] - plot_df["time"].min()).dt.total_seconds().values
                        y_vals = plot_df[col].values
                        if len(x_num) >= 2:
                            slope, intercept = np.polyfit(x_num, y_vals, 1)
                            trend_y = slope * x_num + intercept
                            fig_env.add_trace(
                                go.Scatter(
                                    x=plot_df["time"],
                                    y=trend_y,
                                    mode="lines",
                                    name=f"{col} 추세",
                                    line=dict(dash="dot", color="orange", width=1.5)
                                ),
                                row=i, col=1
                            )
                fig_env.update_layout(
                    height=200 * n + 60,
                    showlegend=False,
                    hovermode="x unified"
                )
                set_fig_font(fig_env)
                st.plotly_chart(fig_env, width="stretch")
            else:
                st.info("환경 데이터에 표시할 열이 없습니다.")

            st.divider()

            # ── 환경 데이터 테이블 ──
            display_cols = [c for c in ["time", "temperature", "humidity", "ph", "ec"] if c in env_df.columns]
            if display_cols:
                st.dataframe(env_df[display_cols].sort_values("time", ascending=False),
                             width="stretch", use_container_width=False)
    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")

# ─────────────────────────────────────────────
# 탭 2: 생육 데이터
# ─────────────────────────────────────────────
with tab2:
    try:
        if growth_df is None or growth_df.empty:
            st.info("생육 CSV가 업로드되지 않았거나 데이터가 없습니다.")
        else:
            # ── 개체번호 범위 안내 ──
            if "개체번호" in growth_df.columns and growth_df["개체번호"].notna().any():
                ids = growth_df["개체번호"].dropna()
                st.caption(f"📋 개체 수: {len(ids)}개  |  범위: {ids.min()} ~ {ids.max()}")

            # ── 생육 지표 요약 카드 ──
            growth_metric_items = [
                ("잎 수", "잎 수"),
                ("지상부 길이", "지상부 길이 (mm)"),
                ("지하부 길이", "지하부 길이 (mm)"),
                ("생중량", "생중량 (g)"),
            ]
            mcols = st.columns(4)
            for col, (key, label) in zip(mcols, growth_metric_items):
                if key in growth_df.columns:
                    vals = growth_df[key].dropna()
                    if len(vals) >= 2:
                        col.metric(label, f"{vals.mean():.1f}", delta=None)
                    else:
                        col.metric(label, "데이터 부족")
                else:
                    col.metric(label, "–")

            st.divider()

            # ── 막대: 개체별 생중량 (상위·하위 3개 강조) ──
            if "생중량" in growth_df.columns and "개체번호" in growth_df.columns:
                gx = growth_df[["개체번호", "생중량"]].dropna()
                if len(gx) >= 2:
                    gx_sorted = gx.sort_values("생중량", ascending=False).reset_index(drop=True)
                    top3 = gx_sorted.head(3)
                    bottom3 = gx_sorted.tail(3)
                    fig_bar = go.Figure()
                    colors = []
                    for _, row in gx_sorted.iterrows():
                        if row["개체번호"] in top3["개체번호"].values:
                            colors.append("#2ecc71")   # 초록: 상위
                        elif row["개체번호"] in bottom3["개체번호"].values:
                            colors.append("#e74c3c")   # 빨강: 하위
                        else:
                            colors.append("#95a5a6")   # 회색: 중간
                    fig_bar.add_trace(go.Bar(
                        x=gx_sorted["개체번호"].astype(str),
                        y=gx_sorted["생중량"],
                        marker_color=colors,
                        hovertext=[f"개체 {i}" for i in gx_sorted["개체번호"]],
                        hoverinfo="x+y+text"
                    ))
                    fig_bar.update_layout(
                        title="개체별 생중량 (초록: 상위 3, 빨강: 하위 3)",
                        xaxis_title="개체번호",
                        yaxis_title="생중량 (g)",
                        height=420
                    )
                    set_fig_font(fig_bar)
                    st.plotly_chart(fig_bar, width="stretch")

            st.divider()

            # ── 산점도 행렬: 잎 수 vs 지상부 길이 vs 생중량 ──
            scatter_pairs = [
                ("잎 수", "지상부 길이", "잎 수 vs 지상부 길이"),
                ("잎 수", "생중량", "잎 수 vs 생중량"),
                ("지상부 길이", "생중량", "지상부 길이 vs 생중량"),
            ]
            for xkey, ykey, title in scatter_pairs:
                if xkey in growth_df.columns and ykey in growth_df.columns:
                    gxy = growth_df[[xkey, ykey]].dropna()
                    if len(gxy) >= 2:
                        x_v = gxy[xkey].values
                        y_v = gxy[ykey].values
                        slope, intercept = np.polyfit(x_v, y_v, 1)
                        r = np.corrcoef(x_v, y_v)[0, 1]
                        fig_sc = go.Figure()
                        fig_sc.add_trace(go.Scatter(
                            x=x_v, y=y_v,
                            mode="markers",
                            marker=dict(size=8, color="steelblue", opacity=0.7),
                            name="데이터"
                        ))
                        x_line = np.array([x_v.min(), x_v.max()])
                        y_line = slope * x_line + intercept
                        fig_sc.add_trace(go.Scatter(
                            x=x_line, y=y_line,
                            mode="lines",
                            name=f"추세 (r={r:.2f})",
                            line=dict(color="orange", dash="dot", width=2)
                        ))
                        fig_sc.update_layout(
                            title=f"{title}  (상관계수 r = {r:.2f})",
                            xaxis_title=xkey,
                            yaxis_title=ykey,
                            height=360,
                            showlegend=True
                        )
                        set_fig_font(fig_sc)
                        st.plotly_chart(fig_sc, width="stretch")
                    else:
                        st.info(f"{title}: 데이터가 부족해 표시할 수 없습니다.")
                else:
                    st.info(f"{title}: 필요한 열이 없습니다.")

            st.divider()

            # ── 생중량 상위/하위 개체 테이블 ──
            if "생중량" in growth_df.columns:
                gx2 = growth_df[["개체번호", "생중량"]].dropna().sort_values("생중량", ascending=False)
                if len(gx2) >= 2:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**🏆 생중량 상위 5개체**")
                        st.dataframe(gx2.head(5), width="stretch", use_container_width=False)
                    with c2:
                        st.markdown("**🔻 생중량 하위 5개체**")
                        st.dataframe(gx2.tail(5).sort_values("생중량"), width="stretch", use_container_width=False)

            st.divider()

            # ── 생육 데이터 테이블 ──
            grow_display = [c for c in growth_df.columns if c != "time"]
            if grow_display:
                st.dataframe(growth_df[grow_display].sort_values("개체번호"),
                             width="stretch", use_container_width=False)

            # ── CSV 다운로드 버튼 ──
            st.divider()
            csv_out = growth_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 생육 데이터 CSV 다운로드",
                data=csv_out,
                file_name=f"{school_name or 'growth'}_생육데이터.csv",
                mime="text/csv"
            )
    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")

# ─────────────────────────────────────────────
# 탭 3: 종합 분석
# ─────────────────────────────────────────────
with tab3:
    try:
        if env_df is None or env_df.empty or growth_df is None or growth_df.empty:
            st.info("두 CSV가 모두 필요합니다. 환경 CSV와 생육 CSV를 모두 업로드해 주세요.")
        else:
            st.markdown("### 환경 vs 생육 종합 비교")

            # 환경 데이터 시간대별 평균 (일 단위로 집계)
            if "time" in env_df.columns:
                env_ts = env_df.copy()
                env_ts["date"] = env_ts["time"].dt.date
                agg_cols = [c for c in ["temperature", "humidity", "ph", "ec"] if c in env_ts.columns]
                if agg_cols:
                    daily = env_ts.groupby("date")[agg_cols].mean().reset_index()
                    daily["date"] = pd.to_datetime(daily["date"])

                    fig_daily = make_subplots(
                        rows=2, cols=2,
                        subplot_titles=["일별 평균 온도", "일별 평균 습도",
                                        "일별 평균 pH", "일별 평균 EC"]
                    )
                    daily_items = [
                        ("temperature", "temperature", 1, 1),
                        ("humidity", "humidity", 1, 2),
                        ("ph", "ph", 2, 1),
                        ("ec", "ec", 2, 2),
                    ]
                    for key, lbl, r, c in daily_items:
                        if key in daily.columns:
                            fig_daily.add_trace(
                                go.Scatter(
                                    x=daily["date"],
                                    y=daily[key],
                                    mode="lines+markers",
                                    name=lbl,
                                    line=dict(color="teal", width=1.5),
                                    marker=dict(size=4)
                                ),
                                row=r, col=c
                            )
                    fig_daily.update_layout(
                        height=480,
                        showlegend=False,
                        hovermode="x unified"
                    )
                    set_fig_font(fig_daily)
                    st.plotly_chart(fig_daily, width="stretch")

            st.divider()

            # 생육 요약 통계 테이블
            if "개체번호" in growth_df.columns:
                stats_cols = [c for c in ["잎 수", "지상부 길이", "지하부 길이", "생중량",
                                          "지상부 질량", "지하부 질량"]
                              if c in growth_df.columns]
                if stats_cols:
                    summary = growth_df[stats_cols].describe().round(2)
                    summary.index = ["개수", "평균", "표준편차", "최소", "25%", "50%", "75%", "최대"]
                    st.markdown("### 생육 지표 요약 통계")
                    st.dataframe(summary, width="stretch", use_container_width=False)

            st.divider()

            # 상관 행렬 히트맵 스타일 표 (상관계수만 표시)
            corr_keys = [c for c in ["잎 수", "지상부 길이", "지하부 길이", "생중량",
                                     "지상부 질량", "지하부 질량"]
                         if c in growth_df.columns]
            if len(corr_keys) >= 2:
                corr_df = growth_df[corr_keys].dropna().corr().round(2)
                st.markdown("### 생육 지표 간 상관계수 행렬")
                st.dataframe(corr_df, width="stretch", use_container_width=False)

            st.divider()

            # 환경-생육 연결 안내
            st.info("💡 종합 분석 안내:\n"
                    "- 탭1의 환경 시계열에서 온도·습도·pH·EC 변화와 생육 추이를 함께 살펴보세요.\n"
                    "- 탭2의 개체별 생중량 막대그래프에서 상위/하위 개체를 확인하고,\n"
                    "  산점도로 생육 지표 간 관계를 점검할 수 있습니다.\n"
                    "- 탭3의 일별 평균 환경 그래프와 생육 통계를 함께 보면\n"
                    "  환경 조건과 생육 결과 간의 경향성을 비교할 수 있습니다.")
    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")
