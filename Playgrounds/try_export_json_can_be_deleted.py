import os

#origin_json_path = "C:/Users/joerr/Documents/GitHub/self-initiative-project-2/receipt_test.json"


#with open("C:/Users/joerr/Documents/GitHub/self-initiative-project-2/receipt_test.json", "r", encoding="utf-8") as fp:
    #d = json.load(fp)

#print(d)


"""folder_path_1 = "C:/Users/joerr/Desktop/ocr project"
text_folder = "txt"
json_folder = "json"
txt_folder_path = os.path.join(folder_path_1,text_folder)

file_names_in_the_folder = [os.path.splitext(file)[0] 
                            for file in os.listdir(txt_folder_path) 
                            if file.lower().endswith(".txt")
                            and os.path.isfile(os.path.join(txt_folder_path , file))]

for image_name in file_names_in_the_folder:
    image_name_in_folder_path = os.path.join(folder_path_1, text_folder, f"{image_name}.txt")

    with open(os.path.join(folder_path_1, json_folder, f"{image_name}.json"), 'w',encoding="utf-8") as json_file:
        json.dump(d, json_file)"""




"""
from OCR_step_2 import raw_txt_to_json
input_folder = "C:/Users/joerr/Desktop/Receipts1"
folder_path_1 = "C:/Users/joerr/Desktop/ocr project"
text_folder = "txt"
json_folder = "json"
txt_folder_path = os.path.join(folder_path_1,text_folder)

file_names_in_the_folder = [os.path.splitext(file)[0] 
                            for file in os.listdir(txt_folder_path) 
                            if file.lower().endswith(".txt")
                            and os.path.isfile(os.path.join(txt_folder_path , file))]

for image_name in file_names_in_the_folder:
    image_name_in_folder_path = os.path.join(folder_path_1, text_folder, f"{image_name}.txt")

    raw_txt_to_json(image_name_in_folder_path , input_receipt_name = image_name , folder_path = folder_path_1, json_folder = json_folder)
"""

from OCR_step_1 import batch_ocr
from OCR_step_2 import raw_txt_to_json
input_folder = "C:/Users/joerr/Desktop/Receipts1"
folder_path_1 = "C:/Users/joerr/Desktop/ocr project"
text_folder = "txt"
json_folder = "json"
txt_folder_path = os.path.join(folder_path_1,text_folder)

#batch_ocr(input_folder, output_folder = txt_folder_path)

# 1. 先取出 txt 資料夾中所有「不含副檔名」的 txt 檔
txt_names = {
    os.path.splitext(file)[0]
    for file in os.listdir(txt_folder_path)
    if file.lower().endswith(".txt")
    and os.path.isfile(os.path.join(txt_folder_path, file))
}

# 2. 比對 input 圖片檔名
file_names_in_the_folder = [os.path.splitext(image)[0] 
                            for image in os.listdir(input_folder)
                            if os.path.splitext(image)[0] in txt_names
                            ]

print(file_names_in_the_folder)

for image_name in file_names_in_the_folder:
    image_name_in_folder_path = os.path.join(folder_path_1, text_folder, f"{image_name}.txt")

    raw_txt_to_json(image_name_in_folder_path , input_receipt_name = image_name , folder_path = folder_path_1, json_folder = json_folder)



"""
input_folder = "C:/Users/joerr/Desktop/Receipts1"
folder_path_1 = "C:/Users/joerr/Desktop/ocr project"
text_folder = "txt"
json_folder = "json"
txt_folder_path = os.path.join(folder_path_1,text_folder)


"""
