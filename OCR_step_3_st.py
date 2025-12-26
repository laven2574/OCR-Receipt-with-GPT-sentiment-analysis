import streamlit as st
import pandas as pd
import os
import json
import shutil
import fitz  # PyMuPDF
import numpy as np
import cv2
from PIL import Image
from paddleocr import PaddleOCR
from openai import OpenAI
import re
from io import BytesIO
from xlsxwriter import Workbook

from OCR_step_1_st import parse_ocr_result
from OCR_step_1_st import process_file_ocr
from OCR_step_2_st import raw_txt_to_json

# --- 頁面設定 ---
st.set_page_config(page_title="收據自動化辨識系統", layout="wide")

# --- 初始化 PaddleOCR (加上 cache 避免重複載入) ---
@st.cache_resource
def load_ocr_model():
    #PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
    return PaddleOCR(lang='ch')



# --- 3. Streamlit UI 介面 ---
def main():
    # --- 初始化 Session State (用於控制步驟) ---
    if 'current_step' not in st.session_state:
        st.session_state['current_step'] = 1

    st.sidebar.title("⚙️ 設定")
    api_key = st.secrets.get["OPENAI_API_KEY"]
    
    st.title("🧾 收據辨識一條龍系統")
    #st.info("上傳收據 -> OCR 辨識 -> AI 格式化 -> 手動校對 -> 存入 Excel")

    # 顯示目前的進度條
    steps = ["1. 上傳與辨識", "2. 校對資料", "3. 匯出結果"]
    current_progress = st.session_state['current_step']
    st.progress(current_progress / 3, text=f"目前步驟：{steps[current_progress-1]}")

# ==========================================
    # 步驟一：檔案上傳與 OCR 處理
    # ==========================================
    if st.session_state['current_step'] == 1:
        st.header("📂 步驟一：檔案上傳")
        st.info("請上傳收據，系統將自動進行 OCR 與 AI 解析。")

        uploaded_files = st.file_uploader("選擇收據檔案 (支持 JPG, PNG, PDF)", type=['jpg', 'jpeg', 'png', 'pdf'], accept_multiple_files=True)

        if uploaded_files:
            if st.button("🚀 開始批次處理"):
                ocr_model = load_ocr_model()
                all_extracted_data = []
                
                progress_bar = st.progress(0)
                status_text = st.empty()

                for idx, file in enumerate(uploaded_files):
                    status_text.text(f"正在處理: {file.name}...")
                    
                    # 1. OCR
                    txt = process_file_ocr(ocr_model, file)
                    
                    # 2. AI 轉換
                    try:
                        json_data = raw_txt_to_json(txt)
                        if json_data: # 確保 AI 有回傳內容
                            for item in json_data:
                                item['source_file'] = file.name
                            all_extracted_data.extend(json_data)
                        else:
                            st.error(f"⚠️ {file.name}: AI 無法從文字中識別商品資訊。")
                    except Exception as e:
                        # 這裡會捕捉到 API Key 錯誤或網路問題
                        st.error(f"❌ {file.name} 解析失敗。錯誤訊息: {e}")
                    
                    progress_bar.progress((idx + 1) / len(uploaded_files))
                
                # --- 關鍵修正：判斷是否有成功抓取到任何資料 ---
                if len(all_extracted_data) > 0:
                    df = pd.DataFrame(all_extracted_data)
                    
                    # 資料型態預處理 (維持 float 與 datetime)
                    numeric_cols = ['unit_price', 'quantity', 'price_discount', 'total_price']
                    for col in numeric_cols:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    if 'purchase_date' in df.columns:
                        df['purchase_date'] = pd.to_datetime(df['purchase_date'], errors='coerce')

                    st.session_state['temp_df'] = df
                    st.session_state['current_step'] = 2 
                    st.success("辨識成功，即將跳轉至校對頁面...")
                    st.rerun()
                else:
                    # 如果 all_extracted_data 是空的，就不會執行 st.rerun()，用家會留在第一步
                    st.error("❌ 所有檔案皆解析失敗，請檢查 API Key 是否正確，或圖片文字是否清晰。")

    # ==========================================
    # 步驟二：手動修正 (Data Editor)
    # ==========================================
    elif st.session_state['current_step'] == 2:
        st.header("📝 步驟二：手動校對")
        st.warning("請在下方表格校對資料。日期欄位點擊兩下可喚出日曆。")
        
        if 'temp_df' in st.session_state:
            # 設定 Column Config (日曆與數值格式)
            column_config = {
                "purchase_date": st.column_config.DateColumn(
                    "購買日期",
                    help="請選擇購買日期",
                    format="YYYY-MM-DD",
                    step=1,
                    required=False
                ),
                "unit_price": st.column_config.NumberColumn("單價", format="$%.2f"),
                "total_price": st.column_config.NumberColumn("總價", format="$%.2f"),
                "price_discount": st.column_config.NumberColumn("折扣", format="$%.2f"),
                "quantity": st.column_config.NumberColumn("數量", format="%.2f"),
            }

            # 顯示編輯器
            edited_df = st.data_editor(
                st.session_state['temp_df'],
                num_rows="dynamic",
                use_container_width=True,
                column_config=column_config,
                key="editor_step_2" # 給個 Key 避免狀態混亂
            )

            # --- 按鈕區塊 ---
            col1, col2 = st.columns([1, 1])
            
            # 按鈕 1: 回上一步 (回到上傳頁面)
            with col1:
                if st.button("⬅️ 返回上一步 (重新上傳)"):
                    st.session_state['current_step'] = 1
                    # 選擇性：若想保留資料可不刪除，若想清空則 del st.session_state['temp_df']
                    st.rerun()

            # 按鈕 2: 前往下一步
            with col2:
                if st.button("✅ 確認無誤，前往匯出"):
                    # 將編輯後的結果存入 final_edited_df
                    st.session_state['final_edited_df'] = edited_df
                    # 同時更新 temp_df，這樣如果從步驟三按返回，會看到最新的修改結果
                    st.session_state['temp_df'] = edited_df
                    
                    st.session_state['current_step'] = 3
                    st.rerun()

    # ==========================================
    # 步驟三：整合與匯出
    # ==========================================
    elif st.session_state['current_step'] == 3:
        st.header("💾 步驟三：資料匯出")
        st.success("資料校對完成！請選擇如何儲存。")
        
        target_excel = st.file_uploader("選擇要追加的舊 Excel 檔 (若不選則建立新檔)", type=['xlsx'])
        
        final_df = st.session_state.get('final_edited_df', pd.DataFrame())
        
        # 預覽最終資料
        with st.expander("點擊預覽最終資料"):
            st.dataframe(final_df)

        if target_excel:
            try:
                existing_df = pd.read_excel(target_excel)
                final_output = pd.concat([existing_df, final_df], ignore_index=True)
                st.info(f"已與舊檔案合併，共 {len(final_output)} 筆資料。")
            except Exception as e:
                st.error(f"讀取舊檔失敗: {e}")
                final_output = final_df
        else:
            final_output = final_df
            st.info(f"將建立新檔案，共 {len(final_output)} 筆資料。")

        # 產出 Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            final_output_export = final_output.copy()
            if 'purchase_date' in final_output_export.columns:
                 final_output_export['purchase_date'] = pd.to_datetime( final_output_export['purchase_date'],errors='coerce')
                 final_output_export['purchase_date'] = final_output_export['purchase_date'].dt.strftime('%Y-%m-%d')
            final_output_export.to_excel(writer, index=False, sheet_name='Sheet1')
        
        # --- 按鈕區塊 ---
        col_dl, col_back, col_reset = st.columns([2, 1, 1])
        
        # 按鈕 1: 下載
        with col_dl:
             st.download_button(
                label="📥 下載 Excel 檔案",
                data=output.getvalue(),
                file_name="grocery_data_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        # 按鈕 2: 返回修改 (回到步驟二)
        with col_back:
            if st.button("⬅️ 返回修改資料", use_container_width=True):
                st.session_state['current_step'] = 2
                st.rerun()

        # 按鈕 3: 重新開始 (回到步驟一)
        with col_reset:
            if st.button("🔄 重新上傳檔案", use_container_width=True):
                st.session_state['current_step'] = 1
                # 清除相關暫存，確保下次是乾淨的開始
                if 'temp_df' in st.session_state: del st.session_state['temp_df']
                if 'final_edited_df' in st.session_state: del st.session_state['final_edited_df']
                st.rerun()

                
if __name__ == "__main__":
    main()