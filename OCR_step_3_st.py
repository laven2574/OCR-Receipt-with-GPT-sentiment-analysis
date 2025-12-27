import streamlit as st
import pandas as pd
from io import BytesIO
from openai import OpenAI
from PIL import Image
from xlsxwriter import Workbook

from OCR_step_1_st import process_file_ocr
from OCR_step_2_st import raw_txt_to_json


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

    steps = ["1. Upload & Recognition", "2. Data Review", "3. Export Results"]
    current_step = st.session_state["current_step"]
    st.progress(current_step / 3, text=f"Current Step：{steps[current_step - 1]}")

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

                # 1. OCR (Tesseract, Step 1)
                txt = process_file_ocr(file)

                # 2. AI Parsing
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

                # 型態預處理
                numeric_cols = [
                    "unit_price",
                    "quantity",
                    "price_discount",
                    "total_price",
                ]
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")

                if "purchase_date" in df.columns:
                    df["purchase_date"] = pd.to_datetime(
                        df["purchase_date"], errors="coerce"
                    )

                st.session_state["temp_df"] = df
                st.session_state["current_step"] = 2
                st.success("✅ Recognition completed. Proceeding to review page.")
                st.rerun()

            else:
                st.error("❌ All files failed to parse.")
                st.button(
                    "🔄 Start Over",
                    type="primary",
                    on_click=reset_session_state
                )

    # =====================================================
    # Step 2: Manual Review
    # =====================================================
    elif current_step == 2:
        st.header("📝 Step 2: Manual Review")
        st.warning("Please verify the data accuracy. You can edit directly if needed.")

        if "temp_df" in st.session_state:
            column_config = {
                "purchase_date": st.column_config.DateColumn(
                    "購買日期", format="YYYY-MM-DD"
                ),
                "unit_price": st.column_config.NumberColumn(
                    "單價", format="$%.2f"
                ),
                "total_price": st.column_config.NumberColumn(
                    "總價", format="$%.2f"
                ),
                "price_discount": st.column_config.NumberColumn(
                    "折扣", format="$%.2f"
                ),
                "quantity": st.column_config.NumberColumn(
                    "數量", format="%.2f"
                ),
            }

            edited_df = st.data_editor(
                st.session_state["temp_df"],
                num_rows="dynamic",
                use_container_width=True,
                column_config=column_config,
                key="editor_step_2",
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("⬅️ Back to Previous Step"):
                    st.session_state["current_step"] = 1
                    st.rerun()

            with col2:
                if st.button("✅ Confirm & Proceed to Export"):
                    st.session_state["final_edited_df"] = edited_df
                    st.session_state["temp_df"] = edited_df
                    st.session_state["current_step"] = 3
                    st.rerun()

    # =====================================================
    # Step 3: Export
    # =====================================================
    elif current_step == 3:
        st.header("💾 Step 3: Export Data")
        st.success("Data review completed. Please choose an export method.")

        final_df = st.session_state.get(
            "final_edited_df", pd.DataFrame()
        )

        with st.expander("📊 Preview Final Data"):
            st.dataframe(final_df)

        target_excel = st.file_uploader(
            "Select existing file to append (optional)", type=["csv", "xlsx"]
        )

        if target_excel:
            try:
                existing_df = pd.read_csv(target_excel)
                final_output = pd.concat(
                    [existing_df, final_df], ignore_index=True
                )
                st.info(f"Merged successfully. Total: {len(final_output)} records")
            except Exception as e:
                st.error(f"Failed to read existing file：{e}")
                final_output = final_df
        else:
            final_output = final_df

        output = BytesIO()
        export_df = final_output.copy()
        if "purchase_date" in export_df.columns:
            export_df["purchase_date"] = pd.to_datetime(export_df["purchase_date"], errors="coerce").dt.strftime("%Y-%m-%d")

        export_df.to_csv(output, index=False, encoding="utf-8-sig")
        output.seek(0)  # 移到檔案開頭

        col_dl, col_back, col_reset = st.columns([2, 1, 1])

        with col_dl:
            st.download_button(
                "📥 Download CSV",
                data=output.getvalue(),
                file_name="grocery_data_export.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col_back:
            if st.button("⬅️ Back to Edit"):
                st.session_state["current_step"] = 2
                st.rerun()

        with col_reset:
            if st.button("🔄 Start Over"):
                reset_session_state()
                st.rerun()


if __name__ == "__main__":
    main()
