import streamlit as st
import pandas as pd
import os
import json

# --- 1. 定義讀取函數 (加入 Cache 以提升效能) ---
@st.cache_data
def load_json_files(folder_path):
    """
    讀取指定資料夾下的所有 JSON 並轉為 DataFrame
    """
    json_dir = os.path.join(folder_path, "json")
    json_records = []
    
    if not os.path.exists(json_dir):
        return pd.DataFrame() # 回傳空表

    for file_name in os.listdir(json_dir):
        if file_name.lower().endswith(".json"):
            file_path = os.path.join(json_dir, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        json_records.extend(data)
                    elif isinstance(data, dict):
                        json_records.append(data)
            except Exception as e:
                st.warning(f"Error reading {file_name}: {e}")

    if not json_records:
        return pd.DataFrame()

    return pd.DataFrame(json_records)

# --- 2. 定義儲存函數 ---
def save_to_excel(new_df, folder_path, file_name):
    """
    將 DataFrame 存入 Excel，如果檔案存在則追加
    """
    export_file = os.path.join(folder_path, f"{file_name}.xlsx")
    
    try:
        if os.path.exists(export_file):
            existing_df = pd.read_excel(export_file)
            final_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            final_df = new_df
            
        final_df.to_excel(export_file, index=False)
        return True, export_file
    except Exception as e:
        return False, str(e)

# --- 3. Streamlit UI 主邏輯 ---
def main():
    st.title("JSON to Excel Converter")

    # 設定路徑 (實際應用中可能是使用者上傳或輸入路徑)
    folder_path_1 = st.text_input("Input Folder Path", value="./data")
    excl_file_name = st.text_input("Output Excel Name", value="output")

    # 按鈕觸發讀取
    if st.button("Load JSON Data"):
        df = load_json_files(folder_path_1)
        
        if df.empty:
            st.error("No JSON data found or folder does not exist.")
        else:
            # 將資料存入 session_state 以便編輯時不會消失
            st.session_state['current_df'] = df
            st.success(f"Loaded {len(df)} rows.")

    # 顯示與編輯資料
    if 'current_df' in st.session_state:
        st.subheader("Preview & Edit Data")
        st.info("You can directly edit cells below (double click to edit).")
        
        # ★★★ 關鍵改變：使用 data_editor 取代 input/exec ★★★
        #這讓使用者像在 Excel 裡一樣直接修改資料
        edited_df = st.data_editor(st.session_state['current_df'], num_rows="dynamic")

        # 儲存按鈕
        if st.button("Append to Excel"):
            success, msg = save_to_excel(edited_df, folder_path_1, excl_file_name)
            if success:
                st.success(f"Data successfully exported to: {msg}")
                # 選擇性：清空 session state
                # del st.session_state['current_df'] 
            else:
                st.error(f"Failed to save: {msg}")


if __name__ == "__main__":
    main()