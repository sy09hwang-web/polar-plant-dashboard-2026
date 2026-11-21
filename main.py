# ─────────────────────────────────────
# 사이드바: 4개 파일 업로드
# ─────────────────────────────────────
st.sidebar.title("📁 실험 데이터 업로드")

file1 = st.sidebar.file_uploader(
    "환경 데이터 파일",
    type=["csv", "xlsx", "xls"],
    key="file1"
)

file2 = st.sidebar.file_uploader(
    "생육 결과 데이터 파일",
    type=["csv", "xlsx", "xls"],
    key="file2"
)

file3 = st.sidebar.file_uploader(
    "추가 데이터 파일 1",
    type=["csv", "xlsx", "xls", "zip"],
    key="file3"
)

file4 = st.sidebar.file_uploader(
    "추가 데이터 파일 2",
    type=["csv", "xlsx", "xls", "zip"],
    key="file4"
)


# 파일 읽기 함수
def load_file(file):
    if file is None:
        return None

    ext = os.path.splitext(file.name)[1].lower()

    try:
        if ext == ".csv":
            return read_csv_auto(file)

        elif ext in [".xlsx", ".xls"]:
            return pd.read_excel(file)

        elif ext == ".zip":
            st.sidebar.success(f"{file.name} 업로드 완료 (압축파일)")
            return None

    except Exception as e:
        st.error(f"{file.name} 읽기 오류: {e}")
        return None


# 파일 읽기
env_raw = load_file(file1)
growth_raw = load_file(file2)
extra_raw1 = load_file(file3)
extra_raw2 = load_file(file4)

env_df = standardize_columns(env_raw) if env_raw is not None else None
growth_df = standardize_columns(growth_raw) if growth_raw is not None else None

# 업로드 상태 표시
st.sidebar.markdown("---")
st.sidebar.subheader("업로드 상태")

for i, file in enumerate([file1, file2, file3, file4], 1):
    if file is not None:
        st.sidebar.success(f"파일 {i}: {file.name}")
    else:
        st.sidebar.warning(f"파일 {i}: 미업로드")
