import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from openai import OpenAI
from xlsxwriter import Workbook

from OCR_step_1_st import process_file_ocr
from OCR_step_2_st import raw_txt_to_json, CATEGORY_AND_SUBCAT


# -------------------------------------------------
# Page config
# -------------------------------------------------
st.set_page_config(
    page_title="Receipt Automation Recognition System",
    layout="wide"
)


# -------------------------------------------------
# Utils
# -------------------------------------------------
def reset_session_state():
    """清除所有 Session State 並重新開始"""
    st.session_state.clear()


def build_subcat_map() -> dict:
    """建立 category → sub_category list 的映射，供 Step 2 的 SelectboxColumn 使用"""
    return {item["category"]: item["sub_category"] for item in CATEGORY_AND_SUBCAT}


ALL_CATEGORIES = [item["category"] for item in CATEGORY_AND_SUBCAT]
ALL_SUBCATEGORIES = [sc for item in CATEGORY_AND_SUBCAT for sc in item["sub_category"]]


# -------------------------------------------------
# Dashboard (Step 4)
# -------------------------------------------------
def show_dashboard(df: pd.DataFrame):
    st.header("📊 Step 4: Data Dashboard")

    # ---------- Sidebar Filters（模擬 Power BI Slicer）----------
    with st.sidebar:
        st.subheader("🔍 Filters")

        available_categories = df["category"].dropna().unique().tolist()
        sel_category = st.multiselect(
            "Category",
            options=available_categories,
            default=available_categories,
            key="dash_category"
        )

        available_shops = df["shops"].dropna().unique().tolist()
        sel_shop = st.multiselect(
            "Shop",
            options=available_shops,
            default=available_shops,
            key="dash_shop"
        )

        if "purchase_date" in df.columns and df["purchase_date"].notna().any():
            min_date = df["purchase_date"].min()
            max_date = df["purchase_date"].max()
            date_range = st.date_input(
                "Date Range",
                value=(min_date, max_date),
                key="dash_date"
            )
        else:
            date_range = None

    # ---------- Apply Filters ----------
    filtered = df.copy()
    if sel_category:
        filtered = filtered[filtered["category"].isin(sel_category)]
    if sel_shop:
        filtered = filtered[filtered["shops"].isin(sel_shop)]
    if date_range and isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        filtered = filtered[
            (filtered["purchase_date"] >= pd.Timestamp(date_range[0])) &
            (filtered["purchase_date"] <= pd.Timestamp(date_range[1]))
        ]

    if filtered.empty:
        st.warning("No data matches the selected filters.")
        return

    # ---------- KPI Cards ----------
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Total Spend",    f"${filtered['total_price'].sum():,.2f}")
    k2.metric("🛒 Total Items",    f"{len(filtered)}")
    k3.metric("📦 Avg Unit Price", f"${filtered['unit_price'].mean():,.2f}")
    k4.metric("🏷️ Total Discount", f"${filtered['price_discount'].sum():,.2f}")

    st.divider()

    # ---------- Row 1：Category Bar + Sub-category Pie ----------
    r1c1, r1c2 = st.columns(2)

    with r1c1:
        cat_data = (
            filtered.groupby("category")["total_price"]
            .sum().reset_index()
            .sort_values("total_price", ascending=False)
        )
        fig_bar = px.bar(
            cat_data, x="category", y="total_price",
            color="category", title="Spending by Category",
            labels={"total_price": "Total Spend", "category": "Category"}
        )
        fig_bar.update_layout(showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    with r1c2:
        sub_data = (
            filtered.groupby("sub_category")["total_price"]
            .sum().reset_index()
        )
        fig_pie = px.pie(
            sub_data, names="sub_category", values="total_price",
            title="Sub-category Breakdown"
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # ---------- Row 2：Time Series（如有日期）----------
    if "purchase_date" in filtered.columns and filtered["purchase_date"].notna().any():
        ts = (
            filtered.groupby("purchase_date")["total_price"]
            .sum().reset_index()
        )
        fig_line = px.line(
            ts, x="purchase_date", y="total_price",
            title="Spending Over Time", markers=True,
            labels={"total_price": "Total Spend", "purchase_date": "Date"}
        )
        st.plotly_chart(fig_line, use_container_width=True)

    # ---------- Row 3：Top 10 Items + Shop Comparison ----------
    r3c1, r3c2 = st.columns(2)

    with r3c1:
        top_items = (
            filtered.groupby("item_name")["total_price"]
            .sum().sort_values(ascending=False)
            .head(10).reset_index()
        )
        fig_top = px.bar(
            top_items, x="total_price", y="item_name",
            orientation="h", title="Top 10 Items by Spend",
            labels={"total_price": "Total Spend", "item_name": "Item"}
        )
        fig_top.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_top, use_container_width=True)

    with r3c2:
        if filtered["shops"].notna().any():
            shop_data = (
                filtered.groupby("shops")["total_price"]
                .sum().reset_index()
                .sort_values("total_price", ascending=False)
            )
            fig_shop = px.bar(
                shop_data, x="shops", y="total_price",
                color="shops", title="Spending by Shop",
                labels={"total_price": "Total Spend", "shops": "Shop"}
            )
            fig_shop.update_layout(showlegend=False)
            st.plotly_chart(fig_shop, use_container_width=True)

    # ---------- Treemap：Category → Sub-category ----------
    if len(filtered["category"].dropna().unique()) > 1:
        tree_data = (
            filtered.groupby(["category", "sub_category"])["total_price"]
            .sum().reset_index()
        )
        fig_tree = px.treemap(
            tree_data, path=["category", "sub_category"],
            values="total_price", title="Spend Treemap (Category → Sub-category)"
        )
        st.plotly_chart(fig_tree, use_container_width=True)

    st.divider()

    # ---------- Navigation ----------
    col_back, col_reset = st.columns([1, 1])
    with col_back:
        if st.button("⬅️ Back to Export"):
            st.session_state["current_step"] = 3
            st.rerun()
    with col_reset:
        if st.button("🔄 Start Over"):
            reset_session_state()
            st.rerun()


# -------------------------------------------------
# Main App
# -------------------------------------------------
def main():
    # ---------- Session State ----------
    if "current_step" not in st.session_state:
        st.session_state["current_step"] = 1

    # ---------- Sidebar ----------
    st.sidebar.title("⚙️ Settings")
    api_key = st.secrets.get("OPENAI_API_KEY")

    # ---------- Header ----------
    st.title("🧾 Receipt Recognition All-in-One System")

    steps = [
        "1. Upload & Recognition",
        "2. Data Review",
        "3. Export Results",
        "4. Dashboard"
    ]
    current_step = st.session_state["current_step"]
    st.progress(
        current_step / len(steps),
        text=f"Current Step：{steps[current_step - 1]}"
    )

    # =====================================================
    # Step 1: Upload & OCR
    # =====================================================
    if current_step == 1:
        st.header("📂 Step 1: File Upload")
        st.info("Please upload receipt images or PDFs. The system will automatically perform OCR and AI parsing.")

        uploaded_files = st.file_uploader(
            "Select receipt files (JPG / PNG / PDF)",
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=True
        )

        if uploaded_files and st.button("🚀 Start Batch Processing"):
            all_extracted_data = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, file in enumerate(uploaded_files):
                status_text.text(f"Processing：{file.name} ...")

                # 1. OCR (Tesseract + Geometry Correction, Step 1)
                txt = process_file_ocr(file)

                # 2. AI Parsing (Step 2)
                try:
                    json_data = raw_txt_to_json(txt)
                    if json_data:
                        for item in json_data:
                            item["source_file"] = file.name
                        all_extracted_data.extend(json_data)
                    else:
                        st.warning(f"⚠️ {file.name}：No valid item information recognised")
                except Exception as e:
                    st.error(f"❌ {file.name} parsing failed：{e}")

                progress_bar.progress((idx + 1) / len(uploaded_files))

            status_text.empty()

            if all_extracted_data:
                df = pd.DataFrame(all_extracted_data)

                numeric_cols = ["unit_price", "quantity", "price_discount", "total_price"]
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")

                if "purchase_date" in df.columns:
                    df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce")

                st.session_state["temp_df"] = df
                st.session_state["current_step"] = 2
                st.success("✅ Recognition completed. Proceeding to review page.")
                st.rerun()
            else:
                st.error("❌ All files failed to parse.")
                st.button("🔄 Start Over", type="primary", on_click=reset_session_state)

    # =====================================================
    # Step 2: Manual Review
    # =====================================================
    elif current_step == 2:
        st.header("📝 Step 2: Manual Review")
        st.warning("Please verify the data accuracy. You can edit directly if needed.")

        if "temp_df" in st.session_state:

            # ── 首次進入 Step 2 時，快照原始資料作為比對基準 ──────────
            # 只在尚未快照時建立，避免每次 rerun 覆蓋掉基準
            if "original_df" not in st.session_state:
                st.session_state["original_df"] = st.session_state["temp_df"].copy()

            original_df = st.session_state["original_df"]

            # ── 橙色高亮輔助函式 ────────────────────────────────────────
            def highlight_modified(row: pd.Series) -> list[str]:
                """
                逐行比對 edited_df 與 original_df：
                - 若該行 index 在原始資料中不存在（新增行） → 橙色
                - 若任何欄位數值與原始不同 → 橙色
                - 若與原始完全一致 → 無填色
                """
                ORANGE = "background-color: #FF8C00; color: white;"
                NONE   = ""

                if row.name not in original_df.index:
                    # 新增的行
                    return [ORANGE] * len(row)

                orig_row = original_df.loc[row.name]
                for col in row.index:
                    if col not in orig_row.index:
                        continue
                    curr_val = row[col]
                    orig_val = orig_row[col]
                    # NaN vs NaN 視為相同
                    both_nan = (
                        (isinstance(curr_val, float) and pd.isna(curr_val)) and
                        (isinstance(orig_val, float) and pd.isna(orig_val))
                    )
                    if both_nan:
                        continue
                    try:
                        if curr_val != orig_val:
                            return [ORANGE] * len(row)
                    except Exception:
                        pass

                return [NONE] * len(row)
            # ────────────────────────────────────────────────────────────

            column_config = {
                "purchase_date": st.column_config.DateColumn(
                    "購買日期", format="YYYY-MM-DD"
                ),
                "unit_price": st.column_config.NumberColumn(
                    "單價", format="$%.2f"
                ),
                "total_price": st.column_config.NumberColumn(
                    "總價（自動計算）",
                    format="$%.2f",
                    help="唯讀欄位：單價 × 數量 − 折扣，任何數值變動後自動更新",
                ),
                "price_discount": st.column_config.NumberColumn(
                    "折扣", format="$%.2f"
                ),
                "quantity": st.column_config.NumberColumn(
                    "數量", format="%.2f"
                ),
                "category": st.column_config.SelectboxColumn(
                    "Category",
                    options=ALL_CATEGORIES,
                    required=False
                ),
                "sub_category": st.column_config.SelectboxColumn(
                    "Sub-category",
                    options=ALL_SUBCATEGORIES,
                    required=False
                ),
            }

            st.caption(
                "💡 **總價** 為唯讀欄位，根據「單價 × 數量 − 折扣」自動計算，不可直接修改。　"
                "🟠 **橙色行** 表示已被修改，恢復原值後橙色消失。"
            )

            # ── 將 Styler 傳入 data_editor 以顯示橙色高亮 ──────────────
            styled = (
                st.session_state["temp_df"]
                .style
                .apply(highlight_modified, axis=1)
            )

            edited_df = st.data_editor(
                styled,
                num_rows="dynamic",
                use_container_width=True,
                column_config=column_config,
                disabled=["total_price", "source_file"],  # 唯讀欄位
                key="editor_step_2",
            )

            # ── 公式驅動：重新計算 total_price ──────────────────────────
            for col in ["unit_price", "quantity", "price_discount"]:
                if col not in edited_df.columns:
                    edited_df[col] = 0.0

            edited_df["total_price"] = (
                pd.to_numeric(edited_df["unit_price"],     errors="coerce").fillna(0) *
                pd.to_numeric(edited_df["quantity"],       errors="coerce").fillna(0) -
                pd.to_numeric(edited_df["price_discount"], errors="coerce").fillna(0)
            )

            # 存回 session_state，下一個 render cycle 會套用最新高亮
            st.session_state["temp_df"] = edited_df
            # ────────────────────────────────────────────────────────────

            col1, col2 = st.columns(2)
            with col1:
                if st.button("⬅️ Back to Previous Step"):
                    # 返回 Step 1 時清除快照，以便重新上傳後重置基準
                    st.session_state.pop("original_df", None)
                    st.session_state["current_step"] = 1
                    st.rerun()
            with col2:
                if st.button("✅ Confirm & Proceed to Export"):
                    st.session_state["final_edited_df"] = edited_df
                    st.session_state["current_step"] = 3
                    st.rerun()

    # =====================================================
    # Step 3: Export
    # =====================================================
    elif current_step == 3:
        st.header("💾 Step 3: Export Data")
        st.success("Data review completed. Please choose an export method.")

        final_df = st.session_state.get("final_edited_df", pd.DataFrame())
        final_output = final_df.copy()

        with st.expander("📊 Preview Final Data"):
            st.dataframe(final_df)

        target_excel = st.file_uploader(
            "Select existing file to append (optional)", type=["csv", "xlsx"]
        )

        if target_excel:
            try:
                if target_excel.name.lower().endswith(".csv"):
                    existing_df = pd.read_csv(target_excel)
                elif target_excel.name.lower().endswith(".xlsx"):
                    existing_df = pd.read_excel(target_excel)
                else:
                    st.error("Unsupported file format")
                    existing_df = None

                if existing_df is not None:
                    final_output = pd.concat([existing_df, final_df], ignore_index=True)
                    st.info(f"Merged successfully. Total: {len(final_output)} records")

            except Exception as e:
                st.error(f"Failed to read existing file：{e}")
                final_output = final_df.copy()

        output_csv  = BytesIO()
        output_xlsx = BytesIO()

        export_df = final_output.copy()
        if "purchase_date" in export_df.columns:
            export_df["purchase_date"] = (
                pd.to_datetime(export_df["purchase_date"], errors="coerce")
                .dt.strftime("%Y-%m-%d")
            )

        # CSV
        export_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
        output_csv.seek(0)

        # XLSX
        with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="data")
        output_xlsx.seek(0)

        col_csv, col_xlsx, col_dash, col_back, col_reset = st.columns([2, 2, 2, 1, 1])

        with col_csv:
            st.download_button(
                "📥 Download CSV",
                data=output_csv.getvalue(),
                file_name="grocery_data_export.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col_xlsx:
            st.download_button(
                "📥 Download XLSX",
                data=output_xlsx.getvalue(),
                file_name="grocery_data_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        with col_dash:
            if st.button("📊 View Dashboard", use_container_width=True):
                st.session_state["current_step"] = 4
                st.rerun()

        with col_back:
            if st.button("⬅️ Back to Edit"):
                st.session_state["current_step"] = 2
                st.rerun()

        with col_reset:
            if st.button("🔄 Start Over"):
                reset_session_state()
                st.rerun()

    # =====================================================
    # Step 4: Dashboard
    # =====================================================
    elif current_step == 4:
        final_df = st.session_state.get("final_edited_df", pd.DataFrame())
        if final_df.empty:
            st.error("No data available. Please complete Steps 1–3 first.")
            if st.button("⬅️ Back"):
                st.session_state["current_step"] = 3
                st.rerun()
        else:
            show_dashboard(final_df)


if __name__ == "__main__":
    main()