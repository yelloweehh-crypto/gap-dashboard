import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="多檔彙整上線缺口儀表板", layout="wide")

# --- 深色主題 CSS ---
st.markdown("""
<style>
    .stApp {
        background-color: #000000;
        color: #e0e0e0;
    }
    .stMetric label {
        color: #a0a0b0 !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #ffffff !important;
    }
    h1, h2, h3, h4, h5 {
        color: #e0e0e0 !important;
    }
    .stSubheader {
        color: #e0e0e0 !important;
    }
    [data-testid="stMarkdownContainer"] {
        color: #e0e0e0;
    }
    .stButton > button {
        background-color: #1a1a1a;
        color: #A6B6BA;
        border: 1px solid #738488;
    }
    .stButton > button:hover {
        background-color: #738488;
        color: #ffffff;
    }
    .stSelectbox label, .stMultiSelect label {
        color: #a0a0b0 !important;
    }
    .stProgress > div > div > div {
        background-color: #A6B6BA !important;
    }
    .stProgress > div > div {
        background-color: #2a2a2a !important;
    }
    .stDownloadButton > button {
        background-color: #1a1a1a;
        color: #A6B6BA;
        border: 1px solid #738488;
    }
</style>
""", unsafe_allow_html=True)

st.title("多檔彙整上線進度 - 缺口分析儀表板")

# --- Google Sheets 設定 ---
SHEET_ID = "1ssBq9Vx47MjMipfxhlTL90mTriVMHT09"
GID_TARGET = "34105576"
GID_SOURCE = "1680458528"

def build_gsheet_url(sheet_id, gid):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

# --- 讀取資料 ---
@st.cache_data(ttl=300)
def load_data():
    url_target = build_gsheet_url(SHEET_ID, GID_TARGET)
    df_target = pd.read_csv(url_target)
    df_target.columns = ["NO", "來方資料歸屬", "Multi_SRC_TBL", "Table_name", "Sjob_Name", "備註"]

    url_source = build_gsheet_url(SHEET_ID, GID_SOURCE)
    df_source = pd.read_csv(url_source)
    df_source.columns = ["No", "DataBaseName", "TableName", "屬性", "來方子公司",
                         "Query_count", "是否要上雲", "是否已上線", "備註"]

    return df_target, df_source

if st.button("重新讀取 Google Sheet 最新資料"):
    st.cache_data.clear()
    st.rerun()

try:
    df_target, df_source = load_data()
except Exception as e:
    st.error(f"讀取 Google Sheet 失敗: {e}")
    st.info("請確認 Google Sheet 已設定為「知道連結的人可以檢視」")
    st.stop()

# --- 建立比對 ---
df_source["TableName_clean"] = df_source["TableName"].astype(str).str.replace(".csv", "", regex=False).str.replace(".txt", "", regex=False).str.strip().str.upper()
df_target["Table_name_clean"] = df_target["Table_name"].astype(str).str.replace(".csv", "", regex=False).str.replace(".txt", "", regex=False).str.strip().str.upper()

source_status = df_source.drop_duplicates(subset="TableName_clean", keep="first").set_index("TableName_clean")[["是否要上雲", "是否已上線", "來方子公司", "屬性", "備註"]].to_dict("index")

records = []
for _, row in df_target.iterrows():
    table = row["Table_name"]
    table_clean = row["Table_name_clean"]
    info = source_status.get(table_clean, {})
    records.append({
        "NO": row["NO"],
        "Sjob_Name": row["Sjob_Name"],
        "Table_name": table_clean,
        "Multi_SRC_TBL": row["Multi_SRC_TBL"],
        "來方資料歸屬": row["來方資料歸屬"],
        "是否要上雲": info.get("是否要上雲", "未登錄"),
        "是否已上線": info.get("是否已上線", ""),
        "來方子公司": info.get("來方子公司", "未知"),
        "屬性": info.get("屬性", "未知"),
        "來源備註": info.get("備註", ""),
    })

df_merged = pd.DataFrame(records)

def classify_status(row):
    if row["是否要上雲"] == "X":
        return "不上雲"
    elif row["是否已上線"] == "V":
        return "已上線"
    elif row["是否要上雲"] == "V":
        return "待上線(缺口)"
    elif row["是否要上雲"] == "未登錄":
        return "未登錄在來源範圍"
    else:
        return "待確認"

df_merged["狀態"] = df_merged.apply(classify_status, axis=1)

# --- 深色主題配色 ---
color_map = {
    "已上線": "#738488",
    "待上線(缺口)": "#A6B6BA",
    "不上雲": "#D0D8DA",
    "未登錄在來源範圍": "#E1DDD7",
    "待確認": "#EFECE7",
}

plot_layout = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#e0e0e0",
)

# --- 儀表板 KPI ---
st.markdown("---")
col0, col1, col2, col3, col4, col5 = st.columns(6)

total_sjobs = df_merged["Sjob_Name"].nunique()
total_tables = df_merged["Table_name"].nunique()
online_tables = df_merged[df_merged["狀態"] == "已上線"]["Table_name"].nunique()
gap_tables = df_merged[df_merged["狀態"] == "待上線(缺口)"]["Table_name"].nunique()
no_cloud = df_merged[df_merged["狀態"] == "不上雲"]["Table_name"].nunique()
not_registered = df_merged[df_merged["狀態"] == "未登錄在來源範圍"]["Table_name"].nunique()

col0.metric("多檔彙整排程總數", total_sjobs)
col1.metric("目標來源總數 (不重複)", total_tables)
col2.metric("已上線", online_tables)
col3.metric("待上線(缺口)", gap_tables, delta=f"-{gap_tables}" if gap_tables > 0 else "0")
col4.metric("不上雲", no_cloud)
col5.metric("未登錄", not_registered)

online_rate = online_tables / total_tables * 100 if total_tables > 0 else 0
st.progress(online_rate / 100)
st.caption(f"上線完成率: {online_rate:.1f}%")

# --- 各子公司上線進度 ---
st.markdown("---")
st.subheader("各子公司上線進度")

def classify_source_status(row):
    if row["是否要上雲"] == "X":
        return "不上雲"
    elif row["是否已上線"] == "V":
        return "已上線"
    elif row["是否要上雲"] == "V":
        return "待上線(缺口)"
    else:
        return "待確認"

df_source_company = df_source.copy()
df_source_company["狀態"] = df_source_company.apply(classify_source_status, axis=1)
company_status = df_source_company.groupby(["來方子公司", "狀態"]).size().reset_index(name="數量")
fig_stack = px.bar(company_status, x="來方子公司", y="數量", color="狀態",
                   color_discrete_map=color_map, barmode="stack")
fig_stack.update_layout(**plot_layout)
st.plotly_chart(fig_stack, use_container_width=True)

# --- 各 Sjob 上線完整度 ---
st.markdown("---")
st.subheader("各 Sjob 上線完整度")
sjob_summary = df_merged.groupby("Sjob_Name").apply(
    lambda g: pd.Series({
        "總來源數": len(g),
        "已上線數": (g["狀態"] == "已上線").sum(),
        "缺口數": (g["狀態"] == "待上線(缺口)").sum(),
        "不上雲數": (g["狀態"] == "不上雲").sum(),
        "完成率%": round((g["狀態"] == "已上線").sum() / len(g) * 100, 1)
    })
).reset_index()
sjob_summary = sjob_summary.sort_values("完成率%", ascending=True)

fig_heatmap = px.bar(sjob_summary, x="完成率%", y="Sjob_Name", orientation="h",
                     color="完成率%", color_continuous_scale=["#EFECE7", "#E1DDD7", "#D0D8DA", "#A6B6BA", "#738488"],
                     range_color=[0, 100])
fig_heatmap.update_layout(height=max(400, len(sjob_summary) * 25), yaxis_title="", **plot_layout)
st.plotly_chart(fig_heatmap, use_container_width=True)

# --- 排程缺口詳情 ---
st.markdown("---")
st.subheader("排程缺口詳情 — 選擇排程查看缺了哪些表")

sjobs_with_gaps = df_merged[df_merged["狀態"].isin(["待上線(缺口)", "未登錄在來源範圍"])]["Sjob_Name"].unique()
sjobs_with_gaps_sorted = sorted(sjobs_with_gaps)

selected_detail_sjob = st.selectbox(
    "選擇排程 (僅顯示有缺口的)",
    ["-- 請選擇 --"] + sjobs_with_gaps_sorted,
    key="detail_sjob"
)

if selected_detail_sjob != "-- 請選擇 --":
    sjob_data = df_merged[df_merged["Sjob_Name"] == selected_detail_sjob].copy()

    detail_col1, detail_col2, detail_col3, detail_col4 = st.columns(4)
    total = len(sjob_data)
    done = (sjob_data["狀態"] == "已上線").sum()
    gaps = (sjob_data["狀態"] == "待上線(缺口)").sum()
    not_reg = (sjob_data["狀態"] == "未登錄在來源範圍").sum()

    detail_col1.metric("總來源需求", total)
    detail_col2.metric("已上線", done)
    detail_col3.metric("待上線(缺口)", gaps)
    detail_col4.metric("未登錄", not_reg)

    def color_status(val):
        colors = {
            "已上線": "background-color: #738488; color: #ffffff",
            "待上線(缺口)": "background-color: #A6B6BA; color: #000000",
            "不上雲": "background-color: #D0D8DA; color: #000000",
            "未登錄在來源範圍": "background-color: #E1DDD7; color: #000000",
            "待確認": "background-color: #EFECE7; color: #000000",
        }
        return colors.get(val, "")

    st.markdown("##### 完整來源表清單")
    styled_df = sjob_data[["Table_name", "Multi_SRC_TBL", "來方資料歸屬", "來方子公司", "狀態", "來源備註"]].style.map(
        color_status, subset=["狀態"]
    )
    st.dataframe(styled_df, use_container_width=True, height=300)

    gap_detail = sjob_data[sjob_data["狀態"].isin(["待上線(缺口)", "未登錄在來源範圍"])]
    if len(gap_detail) > 0:
        st.markdown("##### 缺口清單（需處理）")
        for _, row in gap_detail.iterrows():
            icon = "🔴" if row["狀態"] == "待上線(缺口)" else "🟡"
            note = f" — {row['來源備註']}" if pd.notna(row["來源備註"]) and row["來源備註"] != "" else ""
            st.markdown(f"{icon} **{row['Table_name']}** (`{row['Multi_SRC_TBL']}`) [{row['狀態']}]{note}")
    else:
        st.success("此排程所有來源皆已就緒！")


# --- 反查：資料表被哪些排程使用 ---
st.markdown("---")
st.subheader("資料表反查 — 查看某張表被哪些排程使用")
st.caption("從來源範圍清單中選擇一張表，列出所有使用該表的多檔彙整排程")

df_source_filtered = df_source[~df_source["屬性"].astype(str).str.strip().isin(["5_歷史表", "4_多檔彙整"])]
all_source_tables = sorted(df_source_filtered["TableName_clean"].dropna().unique().tolist())
selected_lookup_table = st.selectbox("選擇資料表", ["-- 請選擇 --"] + all_source_tables, key="lookup_table")

if selected_lookup_table != "-- 請選擇 --":
    used_by = df_target[df_target["Table_name_clean"] == selected_lookup_table].copy()
    source_info = df_source[df_source["TableName_clean"] == selected_lookup_table].iloc[0] if len(df_source[df_source["TableName_clean"] == selected_lookup_table]) > 0 else None

    if source_info is not None:
        info_col1, info_col2, info_col3, info_col4 = st.columns(4)
        info_col1.metric("子公司", source_info.get("來方子公司", "未知"))
        info_col2.metric("是否要上雲", source_info.get("是否要上雲", "未知"))
        info_col3.metric("是否已上線", "是" if source_info.get("是否已上線") == "V" else "否")
        info_col4.metric("使用此表的排程數", len(used_by))

    if len(used_by) > 0:
        st.markdown("##### 使用此表的排程清單")
        st.dataframe(used_by[["Sjob_Name", "Multi_SRC_TBL", "來方資料歸屬", "備註"]],
                     use_container_width=True, height=250)
    else:
        st.warning("此表目前沒有被任何多檔彙整排程使用")

# --- 篩選與明細 ---
st.markdown("---")
st.subheader("明細查詢")

quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)
with quick_col1:
    if st.button(f"只看未登錄 ({not_registered})"):
        st.session_state["quick_filter"] = ["未登錄在來源範圍"]
with quick_col2:
    if st.button(f"只看缺口 ({gap_tables})"):
        st.session_state["quick_filter"] = ["待上線(缺口)"]
with quick_col3:
    if st.button(f"只看已上線 ({online_tables})"):
        st.session_state["quick_filter"] = ["已上線"]
with quick_col4:
    if st.button("顯示全部"):
        st.session_state["quick_filter"] = df_merged["狀態"].unique().tolist()

default_status = st.session_state.get("quick_filter", ["待上線(缺口)", "未登錄在來源範圍"])

filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
with filter_col1:
    selected_status = st.multiselect("篩選狀態", df_merged["狀態"].unique().tolist(),
                                     default=default_status)
with filter_col2:
    sjob_list = ["全部"] + sorted(df_merged["Sjob_Name"].unique().tolist())
    selected_sjob = st.selectbox("篩選 Sjob", sjob_list)
with filter_col3:
    company_list = ["全部"] + sorted(df_merged["來方子公司"].dropna().unique().tolist())
    selected_company = st.selectbox("篩選子公司", company_list)
with filter_col4:
    source_type_list = ["全部"] + sorted(df_merged["來方資料歸屬"].dropna().unique().tolist())
    selected_source_type = st.selectbox("篩選來方資料歸屬", source_type_list)

filtered = df_merged[df_merged["狀態"].isin(selected_status)]
if selected_sjob != "全部":
    filtered = filtered[filtered["Sjob_Name"] == selected_sjob]
if selected_company != "全部":
    filtered = filtered[filtered["來方子公司"] == selected_company]
if selected_source_type != "全部":
    filtered = filtered[filtered["來方資料歸屬"] == selected_source_type]

st.dataframe(filtered[["NO", "Sjob_Name", "Table_name", "Multi_SRC_TBL",
                        "來方資料歸屬", "來方子公司", "狀態", "來源備註"]],
             use_container_width=True, height=400)

st.download_button("下載篩選結果 CSV", filtered.to_csv(index=False, encoding="utf-8-sig"),
                   "缺口明細.csv", "text/csv")
