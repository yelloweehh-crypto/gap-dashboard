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
    .stApp * {
        user-select: text !important;
        -webkit-user-select: text !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("多檔彙整上線進度 - 缺口分析儀表板")

# --- Google Sheets 設定 ---
SHEET_ID = "1ssBq9Vx47MjMipfxhlTL90mTriVMHT09"
GID_TARGET = "34105576"
GID_SOURCE = "1680458528"
GID_REPLACE = "1998321960"
GID_ASSIGN = "123764221"

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

    url_replace = build_gsheet_url(SHEET_ID, GID_REPLACE)
    df_replace = pd.read_csv(url_replace)
    df_replace.columns = ["原始TableName", "替代表名稱", "替代表是否已上線", "依源子公司", "備註"]
    df_replace["原始TableName_clean"] = df_replace["原始TableName"].astype(str).str.strip().str.upper()
    df_replace["替代表名稱_clean"] = df_replace["替代表名稱"].astype(str).str.strip().str.upper()

    url_assign = build_gsheet_url(SHEET_ID, GID_ASSIGN)
    df_assign = pd.read_csv(url_assign)
    df_assign.columns = ["No", "Sjob_Name", "Owner", "排程狀態"]

    return df_target, df_source, df_replace, df_assign

if st.button("重新讀取 Google Sheet 最新資料"):
    st.cache_data.clear()
    st.rerun()

try:
    df_target, df_source, df_replace, df_assign = load_data()
except Exception as e:
    st.error(f"讀取 Google Sheet 失敗: {e}")
    st.info("請確認 Google Sheet 已設定為「知道連結的人可以檢視」")
    st.stop()

# --- 建立替代表對照 ---
# 原始表 -> 替代表名稱（取第一筆）
replace_map = df_replace.drop_duplicates(subset="原始TableName_clean", keep="first").set_index("原始TableName_clean")["替代表名稱_clean"].to_dict()
# 原始表 -> 替代表是否已上線（從 Replace 清單 C 欄）
replace_online_map = df_replace.drop_duplicates(subset="原始TableName_clean", keep="first").set_index("原始TableName_clean")["替代表是否已上線"].to_dict()

# --- 建立比對 ---
df_source["TableName_clean"] = df_source["TableName"].astype(str).str.replace(".csv", "", regex=False).str.replace(".txt", "", regex=False).str.strip().str.upper()
df_target["Table_name_clean"] = df_target["Table_name"].astype(str).str.replace(".csv", "", regex=False).str.replace(".txt", "", regex=False).str.strip().str.upper()

source_status = df_source.drop_duplicates(subset="TableName_clean", keep="first").set_index("TableName_clean")[["是否要上雲", "是否已上線", "來方子公司", "屬性", "備註"]].to_dict("index")

records = []
for _, row in df_target.iterrows():
    table_clean = row["Table_name_clean"]
    has_replace = table_clean in replace_map
    actual_table = replace_map.get(table_clean, table_clean)

    if has_replace:
        # 有替代表：是否已上線依 Replace 清單 C 欄
        replace_online_val = str(replace_online_map.get(table_clean, "")).strip()
        info = source_status.get(actual_table, {})
        records.append({
            "NO": row["NO"],
            "Sjob_Name": row["Sjob_Name"],
            "Table_name": table_clean,
            "實際來源表": actual_table,
            "Multi_SRC_TBL": row["Multi_SRC_TBL"],
            "來方資料歸屬": row["來方資料歸屬"],
            "是否要上雲": "V",
            "是否已上線": "V" if replace_online_val == "V" else "",
            "來方子公司": info.get("來方子公司", "未知"),
            "屬性": info.get("屬性", "未知"),
            "來源備註": info.get("備註", ""),
            "有替代表": True,
        })
    else:
        # 沒有替代表：用原始表查 actual
        info = source_status.get(table_clean, {})
        records.append({
            "NO": row["NO"],
            "Sjob_Name": row["Sjob_Name"],
            "Table_name": table_clean,
            "實際來源表": "",
            "Multi_SRC_TBL": row["Multi_SRC_TBL"],
            "來方資料歸屬": row["來方資料歸屬"],
            "是否要上雲": info.get("是否要上雲", "未登錄"),
            "是否已上線": info.get("是否已上線", ""),
            "來方子公司": info.get("來方子公司", "未知"),
            "屬性": info.get("屬性", "未知"),
            "來源備註": info.get("備註", ""),
            "有替代表": False,
        })

df_merged = pd.DataFrame(records)

def classify_status(row):
    if row["是否已上線"] == "V":
        return "已上線"
    elif row["是否要上雲"] == "V":
        return "待上線(缺口)"
    elif row["是否要上雲"] == "X":
        return "不上雲"
    elif row["是否要上雲"] == "未登錄":
        return "未登錄在來源範圍"
    else:
        return "待確認"

df_merged["狀態"] = df_merged.apply(classify_status, axis=1)

# --- 替代表對應資訊 ---
replace_lookup = df_replace.groupby("原始TableName_clean").apply(
    lambda g: ", ".join(g["替代表名稱"].astype(str).tolist())
).to_dict()
df_merged["替代表"] = df_merged["Table_name"].map(replace_lookup).fillna("")

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
col0, col1, col2, col3, col4, col5, col6 = st.columns(7)

total_sjobs = df_merged["Sjob_Name"].nunique()
total_tables = df_merged["Table_name"].nunique()
online_tables = df_merged[df_merged["狀態"] == "已上線"]["Table_name"].nunique()
gap_tables = df_merged[df_merged["狀態"] == "待上線(缺口)"]["Table_name"].nunique()
no_cloud = df_merged[df_merged["狀態"] == "不上雲"]["Table_name"].nunique()
not_registered = df_merged[df_merged["狀態"] == "未登錄在來源範圍"]["Table_name"].nunique()
pending_confirm = df_merged[df_merged["狀態"] == "待確認"]["Table_name"].nunique()

col0.metric("多檔彙整排程總數", total_sjobs)
col1.metric("目標來源總數 (不重複)", total_tables)
col2.metric("已上線", online_tables)
col3.metric("待上線(缺口)", gap_tables, delta=f"-{gap_tables}" if gap_tables > 0 else "0")
col4.metric("不上雲", no_cloud)
col5.metric("未登錄", not_registered)
col6.metric("待確認", pending_confirm)

online_rate = online_tables / total_tables * 100 if total_tables > 0 else 0
st.progress(online_rate / 100)
st.caption(f"上線完成率: {online_rate:.1f}%")

# --- KPI 明細展開 ---
with st.expander("📋 點擊查看各指標明細"):
    kpi_tab1, kpi_tab2, kpi_tab3, kpi_tab4, kpi_tab5, kpi_tab6 = st.tabs([
        f"多檔彙整排程 ({total_sjobs})",
        f"已上線 ({online_tables})",
        f"待上線-缺口 ({gap_tables})",
        f"不上雲 ({no_cloud})",
        f"未登錄 ({not_registered})",
        f"待確認 ({pending_confirm})",
    ])
    with kpi_tab1:
        sjob_list_detail = df_merged[["Sjob_Name"]].drop_duplicates().sort_values("Sjob_Name").reset_index(drop=True).pipe(lambda df: df.set_axis(range(1, len(df) + 1)))
        st.dataframe(sjob_list_detail, use_container_width=True, height=300)
    with kpi_tab2:
        online_detail = df_merged[df_merged["狀態"] == "已上線"][["Table_name", "實際來源表", "來方子公司", "替代表"]].drop_duplicates(subset="Table_name").sort_values("Table_name").reset_index(drop=True).pipe(lambda df: df.set_axis(range(1, len(df) + 1)))
        st.dataframe(online_detail, use_container_width=True, height=300)
    with kpi_tab3:
        gap_detail_kpi = df_merged[df_merged["狀態"] == "待上線(缺口)"][["Table_name", "來方子公司", "Sjob_Name", "來源備註"]].drop_duplicates(subset="Table_name").sort_values("Table_name").reset_index(drop=True).pipe(lambda df: df.set_axis(range(1, len(df) + 1)))
        st.dataframe(gap_detail_kpi, use_container_width=True, height=300)
    with kpi_tab4:
        nocloud_detail = df_merged[df_merged["狀態"] == "不上雲"][["Table_name", "來方子公司", "來源備註"]].drop_duplicates(subset="Table_name").sort_values("Table_name").reset_index(drop=True).pipe(lambda df: df.set_axis(range(1, len(df) + 1)))
        st.dataframe(nocloud_detail, use_container_width=True, height=300)
    with kpi_tab5:
        unreg_detail = df_merged[df_merged["狀態"] == "未登錄在來源範圍"][["Table_name", "Sjob_Name", "Multi_SRC_TBL"]].drop_duplicates(subset="Table_name").sort_values("Table_name").reset_index(drop=True).pipe(lambda df: df.set_axis(range(1, len(df) + 1)))
        st.dataframe(unreg_detail, use_container_width=True, height=300)
    with kpi_tab6:
        pending_detail = df_merged[df_merged["狀態"] == "待確認"][["Table_name", "來方子公司", "Sjob_Name", "來源備註"]].drop_duplicates(subset="Table_name").sort_values("Table_name").reset_index(drop=True).pipe(lambda df: df.set_axis(range(1, len(df) + 1)))
        st.dataframe(pending_detail, use_container_width=True, height=300)

# --- 各子公司來源資料表數量 + 各 Sjob 上線完整度（並排） ---
st.markdown("---")

company_table_count = df_source.groupby("來方子公司")["TableName_clean"].nunique().reset_index(name="資料表數量")
company_table_count = company_table_count.sort_values("資料表數量", ascending=False).reset_index(drop=True).pipe(lambda df: df.set_axis(range(1, len(df) + 1)))

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

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("各子公司來源資料表數量")
    fig_donut = px.pie(company_table_count, values="資料表數量", names="來方子公司", hole=0.4,
                       color_discrete_sequence=["#3a4a4e", "#4a5a5e", "#2e4a3e", "#5a6a6e", "#4e5e62", "#3e5048"])
    fig_donut.update_traces(textinfo="label+value", textfont_size=12,
                            textfont_color="#ffffff", textfont_family="Arial Black",
                            marker_line_width=0.5, marker_line_color="#000000",
                            textposition="inside")
    fig_donut.update_layout(height=470, margin=dict(l=0, r=0, t=20, b=20),
                            showlegend=False, **plot_layout)
    st.plotly_chart(fig_donut, use_container_width=True)

with col_right:
    st.subheader("各 Sjob 上線完整度")
    fig_heatmap = px.bar(sjob_summary, x="完成率%", y="Sjob_Name", orientation="h",
                         color="完成率%", color_continuous_scale=["#EFECE7", "#E1DDD7", "#D0D8DA", "#A6B6BA", "#738488"],
                         range_color=[0, 100])
    fig_heatmap.update_layout(height=max(400, len(sjob_summary) * 25), yaxis_title="", **plot_layout)
    st.plotly_chart(fig_heatmap, use_container_width=True)

# --- 排程分配與上線通知 ---
st.markdown("---")
st.subheader("排程分配狀態與上線通知")

# 合併分配清單與完成率
df_assign_status = df_assign.merge(sjob_summary[["Sjob_Name", "完成率%", "總來源數", "已上線數", "缺口數"]], on="Sjob_Name", how="left")
df_assign_status["完成率%"] = df_assign_status["完成率%"].fillna(0)
df_assign_status["已上線數"] = df_assign_status["已上線數"].fillna(0).astype(int)
df_assign_status["缺口數"] = df_assign_status["缺口數"].fillna(0).astype(int)
df_assign_status["來源備齊"] = df_assign_status["完成率%"] == 100

ready_sjobs = df_assign_status[df_assign_status["來源備齊"]]

with st.expander(f"🔔 來源備齊通知（{len(ready_sjobs)} 支可上線）"):
    if len(ready_sjobs) > 0:
        for _, row in ready_sjobs.iterrows():
            owner = row["Owner"] if pd.notna(row["Owner"]) and str(row["Owner"]).strip() != "" else ""
            status = row["排程狀態"] if pd.notna(row["排程狀態"]) and str(row["排程狀態"]).strip() != "" else ""
            st.markdown(f"- **{row['Sjob_Name']}**（Owner: {owner}）排程狀態: {status}")
    else:
        st.info("目前沒有排程來源完全備齊")

st.markdown("##### 各排程分配總覽")

assign_display = df_assign_status[["No", "Sjob_Name", "Owner", "排程狀態", "已上線數", "缺口數"]].pipe(lambda df: df.set_axis(range(1, len(df) + 1)))
st.dataframe(assign_display, use_container_width=True, height=min(500, max(100, 35 * len(assign_display) + 40)))

# --- 排程缺口詳情 ---
st.markdown("---")
st.subheader("排程缺口詳情 — 選擇排程查看缺了哪些表")

all_sjobs_sorted = sorted(df_merged["Sjob_Name"].unique())

selected_detail_sjob = st.selectbox(
    "選擇排程",
    ["-- 請選擇 --"] + all_sjobs_sorted,
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
    styled_df = sjob_data[["Table_name", "實際來源表", "Multi_SRC_TBL", "來方資料歸屬", "來方子公司", "狀態", "替代表", "來源備註"]].style.map(
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
    # 直接使用該表的排程
    used_by_direct = df_target[df_target["Table_name_clean"] == selected_lookup_table].copy()
    used_by_direct["使用方式"] = "直接使用"

    # 該表作為替代表時，找出它替代了哪些原始表，再找那些原始表對應的排程
    replaced_originals = df_replace[df_replace["替代表名稱_clean"] == selected_lookup_table]["原始TableName_clean"].unique()
    used_by_replace = df_target[df_target["Table_name_clean"].isin(replaced_originals)].copy()
    used_by_replace["使用方式"] = "替代 " + used_by_replace["Table_name_clean"]

    used_by = pd.concat([used_by_direct, used_by_replace], ignore_index=True).drop_duplicates(subset=["Sjob_Name", "Table_name_clean"])

    source_rows = df_source[df_source["TableName_clean"] == selected_lookup_table]
    source_info = source_rows.iloc[0] if len(source_rows) > 0 else None

    if source_info is not None:
        company = source_info.get("來方子公司", "")
        company_display = company if pd.notna(company) and str(company).strip() != "" else ""
        attr = source_info.get("屬性", "")
        attr_display = attr if pd.notna(attr) and str(attr).strip() != "" else ""
        upload = source_info.get("是否要上雲", "")
        upload_display = upload if pd.notna(upload) and str(upload).strip() != "" else ""
        online = "是" if source_info.get("是否已上線") == "V" else "否"
        note = source_info.get("備註", "")
        note_display = note if pd.notna(note) and str(note).strip() != "" else ""

        st.markdown(f"""
        <div style="display: flex; gap: 2rem; flex-wrap: wrap; margin: 0.5rem 0 1rem 0; user-select: text; -webkit-user-select: text;">
            <div><span style="color: #a0a0b0; font-size: 0.75rem;">子公司</span><br><span style="color: #fff; font-size: 0.9rem;">{company_display}</span></div>
            <div><span style="color: #a0a0b0; font-size: 0.75rem;">屬性</span><br><span style="color: #fff; font-size: 0.9rem;">{attr_display}</span></div>
            <div><span style="color: #a0a0b0; font-size: 0.75rem;">是否要上雲</span><br><span style="color: #fff; font-size: 0.9rem;">{upload_display}</span></div>
            <div><span style="color: #a0a0b0; font-size: 0.75rem;">是否已上線</span><br><span style="color: #fff; font-size: 0.9rem;">{online}</span></div>
            <div><span style="color: #a0a0b0; font-size: 0.75rem;">使用此表的排程數</span><br><span style="color: #fff; font-size: 0.9rem;">{len(used_by)}</span></div>
            <div><span style="color: #a0a0b0; font-size: 0.75rem;">備註</span><br><span style="color: #fff; font-size: 0.9rem;">{note_display}</span></div>
        </div>
        """, unsafe_allow_html=True)

    if len(used_by) > 0:
        st.markdown("##### 使用此表的排程清單")
        table_height = min(400, max(80, 35 * len(used_by) + 40))
        st.dataframe(used_by[["Sjob_Name", "Multi_SRC_TBL", "來方資料歸屬", "使用方式"]].reset_index(drop=True).pipe(lambda df: df.set_axis(range(1, len(df) + 1))),
                     use_container_width=True, height=table_height)
    else:
        st.warning("此表目前沒有被任何多檔彙整排程使用")

