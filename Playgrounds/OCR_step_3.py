import os
import json
import pandas as pd

# 路徑設定
folder_path_1 = "C:/Users/joerr/Desktop/ocr project"
excl_file_name = "grocery_data_export"
JSON_DIR = os.path.join(folder_path_1, "json")
EXPORT_FILE = os.path.join(folder_path_1, f"{excl_file_name}.xlsx")

# 讀取所有 JSON 檔案
json_records = []

for file_name in os.listdir(JSON_DIR):
    if file_name.lower().endswith(".json"):
        file_path = os.path.join(JSON_DIR, file_name)

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

            # 假設每個 JSON 檔案是一筆資料（dict）
            # 若為 list，則逐筆加入
            if isinstance(data, list):
                json_records.extend(data)
            elif isinstance(data, dict):
                json_records.append(data)
            else:
                raise ValueError(f"Unsupported JSON structure in {file_name}")

# 若沒有任何可匯入資料，直接結束
if not json_records:
    raise ValueError("No valid JSON data found.")

# 建立新的 DataFrame
new_df = pd.DataFrame(json_records)

print("\n===== Preview of new imported data =====")
print(new_df)
print("\nColumns:", list(new_df.columns))
print("Total rows:", len(new_df))

# ======【新增：是否需要修改】======
user_input = input("\nNew data needs to be amended? (y/n): ").strip().lower()

if user_input == "y":
    print("\nYou can now manually modify `new_df`.")
    print("Example commands you may run:")
    print("  new_df.loc[0, 'price'] = 9.99")
    print("  new_df = new_df.drop(index=0)")
    print("  new_df['quantity'] = new_df['quantity'].astype(int)")
    print("When finished, type: done")

    while True:
        cmd = input(">>> ").strip()
        if cmd.strip().lower() == "done":
            break
        try:
            exec(cmd)
            print("\n===== Current new_df =====")
            print(new_df)
        except Exception as e:
            print("Error:", e)

    print("\n===== Updated new_df =====")
    print(new_df)

elif user_input == "n":
    print("Proceeding without modification.")
else:
    raise ValueError("Invalid input. Please enter 'y' or 'n'.")



# 若 Excel 已存在，讀取並追加
if os.path.exists(EXPORT_FILE):
    existing_df = pd.read_excel(EXPORT_FILE)
    final_df = pd.concat([existing_df, new_df], ignore_index=True)
else:
    final_df = new_df

# 匯出 Excel
final_df.to_excel(EXPORT_FILE, index=False)

print(f"Data successfully exported to: {EXPORT_FILE}")