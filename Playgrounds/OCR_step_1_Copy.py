def batch_ocr(input_folder, output_folder):

    from paddleocr import PaddleOCR
    import os
    import shutil
    import fitz


    # === 相容性修補（必須加在這裡或程式最前面）===
    if not hasattr(fitz.Document, "pageCount"):
        fitz.Document.pageCount = property(lambda self: self.page_count)
    if not hasattr(fitz.Page, "getPixmap"):
        fitz.Page.getPixmap = lambda self, **kw: self.get_pixmap(**kw)

    ocr = PaddleOCR(
        lang='ch',
        use_angle_cls=True
        )
    

    os.makedirs(output_folder, exist_ok=True)

    # 專案根目錄（ocr project）
    base_dir = os.path.dirname(os.path.abspath(output_folder))

    # image 輸出目錄
    image_output_folder = os.path.join(base_dir, "image")
    os.makedirs(image_output_folder, exist_ok=True)

    for file in os.listdir(input_folder):
        if not file.lower().endswith(('.jpg', '.png', '.jpeg', '.tiff', '.bmp', '.pdf')):
            continue

        image_path = os.path.join(input_folder, file)
        print(f"Processing: {image_path}")

        # 複製圖片到 output_folder 同一層
        dest_image_path = os.path.join(image_output_folder, file)
        shutil.copy2(image_path, dest_image_path)

        # 執行 OCR
        result = ocr.ocr(image_path, cls=True)

        #移除副檔名
        txt_file_name, _ = os.path.splitext(file)

        # 將文字結果輸出成 txt
        output_text_path = os.path.join(output_folder, txt_file_name + ".txt")

        with open(output_text_path, "w", encoding="utf-8") as out:
            for line in result:
                for word_info in line:
                    if not isinstance(word_info, list) or len(word_info) < 2:
                        continue   # 跳過異常資料（通常是 float）

                    # word_info[1] 應該是 ["文字", score]
                    if not isinstance(word_info[1], list) or len(word_info[1]) < 1:
                        continue

                    text = line[1][0]     # 辨識文字
                    score = word_info[1][1]    # 信心度
                    out.write(f"{text}\n")

        print(f"Saved: {output_text_path}")

# -------------------------------------------
# 3. 使用範例
# -------------------------------------------
if __name__ == "__main__":
    input_folder = "C:/Users/joerr/Desktop/Receipts1"       # 收據圖片資料夾
    output_folder = "C:/Users/joerr/Desktop/ocr project/txt"   # 輸出資料夾
    batch_ocr(input_folder, output_folder)
