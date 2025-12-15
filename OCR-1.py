import os
from paddleocr import PaddleOCR

# -------------------------------------------
# 1. 初始化多語言 OCR 模型
# lang='ch' 支援中英混合（推薦）
# 也可以改：'japan' 'korean' 'latin' 等
# -------------------------------------------
ocr = PaddleOCR(
    use_angle_cls=True,   # 自動旋轉校正（收據很常用）
    lang='ch',            # 中文＋英文混合，處理收據效果最好
    use_gpu=False         # 如果你有 GPU 可以改 True
)

# -------------------------------------------
# 2. 批次 OCR
# -------------------------------------------
def batch_ocr(input_folder, output_folder):

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for file in os.listdir(input_folder):
        if not file.lower().endswith(('.jpg', '.png', '.jpeg', '.tiff', '.bmp', '.pdf')):
            continue

        image_path = os.path.join(input_folder, file)
        print(f"Processing: {image_path}")

        # 執行 OCR
        result = ocr.ocr(image_path, cls=True)

        # 將文字結果輸出成 txt
        output_text_path = os.path.join(output_folder, file + ".txt")
        with open(output_text_path, "w", encoding="utf-8") as out:
            for line in result:
                for word_info in line:
                    text = word_info[1][0]     # 辨識文字
                    score = word_info[1][1]    # 信心度
                    out.write(f"{text}\n")

        print(f"Saved: {output_text_path}")

# -------------------------------------------
# 3. 使用範例
# -------------------------------------------
if __name__ == "__main__":
    input_folder = "C:/Users/joerr/Desktop/Receipts1"       # 收據圖片資料夾
    output_folder = "C:/Users/joerr/Desktop/新增資料夾 (2)"   # 輸出資料夾
    batch_ocr(input_folder, output_folder)