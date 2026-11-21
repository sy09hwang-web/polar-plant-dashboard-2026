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

            # 환경 지표 요약 카드 (온도, 습도, pH, EC, 수온, CO2 대응)
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
                                y=plot_df[col],
                                mode="lines",
                                name=col,
                                line=dict(color="royalblue", width=1.2)
                            ),
                            row=i, col=1
                        )
                        # 추세선 추가
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
                st.plotly_chart(fig_env, use_container_width=True)
            else:
                st.info("환경 데이터에 표시할 열이 없습니다.")

            st.divider()

            # 환경 데이터 테이블
            display_cols = [c for c in ["time"] + available_env_metrics if c in env_df.columns]
            if display_cols:
                st.dataframe(env_df[display_cols].sort_values("time", ascending=False), use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ 환경 데이터 처리 중 문제가 발생했습니다: {e}")

# ─────────────────────────────────────────────
# 탭 2: 생육 데이터
# ─────────────────────────────────────────────
with tab2:
    try:
        if growth_df is None or growth_df.empty:
            st.info("생육 데이터가 업로드되지 않았거나 데이터가 없습니다.")
        else:
            if "개체번호" in growth_df.columns and growth_df["개체번호"].notna().any():
                ids = growth_df["개체번호"].dropna()
                st.caption(f"📋 개체 수: {len(ids)}개  |  범위: {int(ids.min())} ~ {int(ids.max())}")

            # 생육 지표 요약 카드
            growth_metric_items = [
                ("잎 수", "잎 수 (장)"),
                ("지상부 길이", "지상부 길이 (mm)"),
                ("지하부 길이", "지하부 길이 (mm)"),
                ("생중량", "생중량 (g)"),
            ]
            mcols = st.columns(4)
            for i, (key, label) in enumerate(growth_metric_items):
                if key in growth_df.columns:
                    vals = growth_df[key].dropna()
                    with mcols[i]:
                        if len(vals) >= 2:
                            st.metric(label, f"{vals.mean():.1f}")
                        else:
                            st.metric(label, "데이터 부족")
                else:
                    with mcols[i]:
                        st.metric(label, "–")

            st.divider()

            # 개체별 생중량 막대그래프 (상위·하위 3개 강조)
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
                        hovertext=[f"개체 {int(i)}" for i in gx_sorted["개체번호"]],
                        hoverinfo="x+y+text"
                    ))
                    fig_bar.update_layout(
                        title="개체별 생중량 (초록: 상위 3, 빨강: 하위 3)",
                        xaxis_title="개체번호",
                        yaxis_title="생중량 (g)",
                        height=420
                    )
                    set_fig_font(fig_bar)
                    st.plotly_chart(fig_bar, use_container_width=True)

            st.divider()

            # 산점도: 생육 지표 간 관계
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
                        st.plotly_chart(fig_sc, use_container_width=True)

            st.divider()

            # 생중량 상위/하위 개체 테이블
            if "생중량" in growth_df.columns:
                gx2 = growth_df[["개체번호", "생중량"]].dropna().sort_values("생중량", ascending=False)
                if len(gx2) >= 2:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**🏆 생중량 상위 5개체**")
                        st.dataframe(gx2.head(5), use_container_width=True)
                    with c2:
                        st.markdown("**🔻 생중량 하위 5개체**")
                        st.dataframe(gx2.tail(5).sort_values("생중량"), use_container_width=True)

            st.divider()

            # 전체 생육 데이터 테이블 및 다운로드
            grow_display = [c for c in growth_df.columns if c != "time"]
            if grow_display:
                st.dataframe(growth_df[grow_display].sort_values("개체번호"), use_container_width=True)

            st.divider()
            csv_out = growth_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 생육 데이터 CSV 다운로드",
                data=csv_out,
                file_name=f"{school_name or 'growth'}_생육데이터.csv",
                mime="text/csv"
            )
    except Exception as e:
        st.warning(f"⚠️ 생육 데이터 처리 중 문제가 발생했습니다: {e}")

# ─────────────────────────────────────────────
# 탭 3: 종합 분석
# ─────────────────────────────────────────────
with tab3:
    try:
        if env_df is None or env_df.empty or growth_df is None or growth_df.empty:
            st.info("환경 및 생육 데이터가 모두 필요합니다. 사이드바에서 두 파일을 모두 업로드해 주세요.")
        else:
            st.markdown("### 환경 vs 생육 종합 비교")

            if "time" in env_df.columns:
                env_ts = env_df.copy()
                env_ts["date"] = env_ts["time"].dt.date
                agg_cols = [c for c in ["temperature", "humidity", "ph", "ec", "수온", "CO2"] if c in env_ts.columns]
                if agg_cols:
                    daily = env_ts.groupby("date")[agg_cols].mean().reset_index()
                    daily["date"] = pd.to_datetime(daily["date"])

                    n_cols = 2
                    n_rows = (len(agg_cols) + 1) // 2
                    fig_daily = make_subplots(
                        rows=n_rows, cols=n_cols,
                        subplot_titles=[labels_map.get(c, c) for c in agg_cols]
                    )
                    for idx, col in enumerate(agg_cols):
                        r = idx // n_cols + 1
                        c = idx % n_cols + 1
                        fig_daily.add_trace(
                            go.Scatter(
                                x=daily["date"],
                                y=daily[col],
                                mode="lines+markers",
                                name=col,
                                line=dict(color="teal", width=1.5),
                                marker=dict(size=4)
                            ),
                            row=r, col=c
                        )
                    fig_daily.update_layout(
                        height=240 * n_rows + 60,
                        showlegend=False,
                        hovermode="x unified"
                    )
                    set_fig_font(fig_daily)
                    st.plotly_chart(fig_daily, use_container_width=True)

            st.divider()

            # 생육 요약 통계 및 상관계수 행렬
            stats_cols = [c for c in ["잎 수", "지상부 길이", "지하부 길이", "생중량", "지상부 질량", "지하부 질량"] if c in growth_df.columns]
            if stats_cols:
                summary = growth_df[stats_cols].describe().round(2)
                summary.index = ["개수", "평균", "표준편차", "최소", "25%", "50%", "75%", "최대"]
                st.markdown("### 생육 지표 요약 통계")
                st.dataframe(summary, use_container_width=True)

            st.divider()

            if len(stats_cols) >= 2:
                corr_df = growth_df[stats_cols].dropna().corr().round(2)
                st.markdown("### 생육 지표 간 상관계수 행렬")
                st.dataframe(corr_df, use_container_width=True)

            st.divider()

            st.info("💡 종합 분석 안내:\n"
                    "- 탭1의 환경 시계열에서 온도·습도·pH·EC·수온·CO2 변화와 생육 추이를 함께 살펴보세요.\n"
                    "- 탭2의 개체별 생중량 막대그래프에서 상위/하위 개체를 확인하고, 산점도로 지표 간 관계를 점검할 수 있습니다.\n"
                    "- 탭3의 일별 평균 환경 그래프와 생육 통계를 통해 재배 환경과 식물 생육 결과의 상관관계를 다각도로 비교해 보세요.")
    except Exception as e:
        st.warning(f"⚠️ 종합 분석 처리 중 문제가 발생했습니다: {e}")
```[cite: 1]
