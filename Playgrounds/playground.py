import os
from openai import OpenAI
import re
import json

output_folder = "C:/Users/joerr/Desktop/ocr project/txt"   # 輸出資料夾
txt_file_name = "receipt_test_1"
txt_path = os.path.join(output_folder, txt_file_name + ".txt")


def temp_func(text_path : str):

    def read_txt_file(file_path):
        """ Reads a text file and returns its content """
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    txt_content = read_txt_file(text_path)
    #txt_content = read_txt_file(f"C:/Users/joerr/Desktop/ocr project/txt/{txt_file_name}.txt")

    client = OpenAI(api_key= apikey)

    response = client.responses.create(
        model="gpt-4.1",
        input=[
            {
                "role": "system",
                "content": "用專業的態度，請不用無中生有原本沒有的資料或錯誤的資訊；若不懂請直接說不明白或不清楚。你是一名擁有十年經驗的 accounts payable specialist。"
            },
            {
                "role": "user",
                "content": (
                    "現在需要你在這堆 raw data 中判斷這是否為收據的 RAW DATA。"
                    "如果不是，請直接說明不是收據的 RAW DATA 並結束任務。"
                    "如果是收據，按照以下步驟完成任務：\n"
                    "1. 目標結果資料的headers 為item_name, unit_price, quantity, price_discount, total_price, shops, branch, brand, category, sub-category, packing_type, unit_type\n"
                    "2. raw data 只保留購買項目、價錢、超級市場名稱、分店、數量（如有）\n"
                    "3. 每個項目生成 5 個 tags（品牌、主分類、次分類、包裝型式、容量/重量）\n"
                    "4. 如果某一行資料是折扣的話需要合併回原本的商品, 並更新total_price, 還有在price_discount中新增折扣數值\n"
                    "5. 以JSON形式輸出\n\n"
                    "以下是 RAW DATA：\n\n"
                    f"{txt_content}"
                            )
            }
                                    ]
                                        )
        
    raw_text = response.output[0].content[0].text

    def extract_json_from_response(text: str):
        pattern = r"```json\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL)

        if not match:
            raise ValueError("Response 中沒有找到 JSON block")

        json_str = match.group(1)

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 格式錯誤: {e}")
        
    parsed_data = extract_json_from_response(raw_text)

    with open("C:/Users/joerr/Desktop/ocr project/json/receipt_test_1.json", 'w') as json_file:
        json.dump(parsed_data, json_file)

    #with open(f"{image_name}.json", 'w') as json_file:
        #json.dump(parsed_data, json_file)


    return print("Successfully saved")

temp_func(txt_path)