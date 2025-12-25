from openai import OpenAI
import re
import json
import os


def raw_txt_to_json(the_image_path, input_receipt_name , folder_path , json_folder):

    def read_txt_file(file_path):
        """ Reads a text file and returns its content """
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    txt_content = read_txt_file(the_image_path)

    #記得DEL 呢條API KEY
    apikey = "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"
    client = OpenAI(api_key= apikey)

    """
    category = ['Fruit and Vegetables', 'Meat, Poultry and Seafood', 'Fridge, Deli and Eggs', 'Bakery', 'Frozen', 
                    'Pantry', 'Beer, Wine and Cider', 'Health and Body', 'Baby and Child', 'Pets', 'Household', 
                    'Snacks, Treats and Easy Meals']
    """

    category_and_subcat = [{"category": "Food and Beverages", "sub_category" :['Beverages','Rice','Noodle and Pasta', 'Oil','Baking and Dessert Needs','Canned', 
                                                                               'Preserved and Dried Food', 'Condiment, Sauce and Soup','Snack and Dessert','Chilled or Frozen Food',
                                                                               'Fruit and Vegetable', 'Breakfast, Bakery and Jam' , 'Meat, Poultry and Seafood'] },
                           {"category": "Baby and Mum", "sub_category" :['Baby Milk Formula', 'Baby Diaper and Pant Baby Food', 'Baby Care', 'Other Baby Needs', 'Prenatal and Postnatal Care'] },
                           {"category": "Personal Care and Health", "sub_category" :['Oral Care','Body Care','Hair Care','Hand and Foot Care','Feminine Care',
                                                                                     'Beauty Care','Mens Shaving Care','Condoms and Sexual Wellness','Adult Care','Medicine','Health and Wellness']},
                            {"category": "Household", "sub_category" :['Toilet Roll and Tissue','Household Cleaner','Kitchen Cleaner','Bathroom Cleaner','Laundry',
                                                                       'Kitchenware and Tableware','Home Eletronic and AC Digital','Houseware and Party Supplies','Travel and Gardenware','Home Care'] },
                            {"category": "Pet Zone", "sub_category" :['Cat Care','Dog Care','Other Pets','Pet Safe Cleaner','Pet Food','Pet Supplies'] },
                            
                            ]
    

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
                    "你需要判斷以下 RAW DATA 是否為『收據的原始資料（Receipt RAW DATA）』。\n\n"

                    "【判斷規則】\n"
                    "若內容不包含實際購買項目與價格資訊，請直接輸出：\n"
                    "「這不是收據的 RAW DATA」並結束任務，不要輸出任何其他內容。\n\n"

                    "若判定為收據的 RAW DATA，請依照以下規則處理並輸出結果：\n\n"

                    "【輸出資料欄位（headers）】\n"
                    "item_name, unit_price, quantity, price_discount, total_price, "
                    "shops, branch, brand, category, sub_category, packing_type, unit_type, purchase_date\n\n"

                    "【資料抽取規則】\n"
                    "1. 僅保留與購買項目相關的資料，包括：商品名稱、價格、數量（如有）、"
                    "超級市場名稱、分店名稱、購買日期（如有）。\n"
                    "2. 若某一行為折扣資料，請將該折扣合併回對應的商品項目，"
                    "更新 total_price，並在 price_discount 中填入折扣金額。\n"
                    "3. 若 RAW DATA 中包含日期，請統一轉換為 mm/dd/yyyy 格式；"
                    "若無日期資訊，purchase_date 請留空。\n"
                    "4. item_name 僅能保留單一語言。"
                    "若同一商品同時出現英文與中文名稱，請優先使用英文；"
                    "若僅有中文，則使用中文。"
                    "請勿自行翻譯或推測未明確出現在 RAW DATA 中的名稱。\n\n"

                    "【分類規則】\n"
                    "4. 每個商品項目必須指定一個主分類（category）與一個次分類（sub_category），"
                    "且分類名稱僅能從以下清單中選擇，不可自行新增：\n"
                    f"{category_and_subcat}\n\n"

                    "【Tags 規則】\n"
                    "5. 每個商品項目需產生一個 tags 欄位，"
                    "tags 為一個陣列（array），內容包含以下三項：\n"
                    "- brand\n"
                    "- category\n"
                    "- sub_category\n\n"

                    "【輸出格式】\n"
                    "6. 請以 JSON Array 形式輸出，每一個商品為一個 object，"
                    "所有 key 必須與 headers 名稱完全一致。\n"
                    "7. 若某欄位無資料，請使用空字串 \"\"。\n\n"

                    "以下是 RAW DATA：\n\n"
                    f"{txt_content}"
                        )
        }
                                ]
                                    )
    
    raw_text = response.output[0].content[0].text

    def extract_json_from_response(text: str):
        pattern = r"(\[\s*\{.*?\}\s*\])"
        match = re.search(pattern, text, re.DOTALL)

        if not match:
            raise ValueError("Response 中沒有找到 JSON block")

        json_str = match.group(1)

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 格式錯誤: {e}")
    
    parsed_data = extract_json_from_response(raw_text)

    json_export = os.path.join(folder_path, json_folder, f"{input_receipt_name}.json")
    with open(json_export, 'w', encoding="utf-8" ) as json_file:
        json.dump(parsed_data, json_file, indent=2 , ensure_ascii=False)

    print("Text to Json process has been done!")