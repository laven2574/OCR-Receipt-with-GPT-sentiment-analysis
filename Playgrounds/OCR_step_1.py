def batch_ocr(input_folder, output_folder):
    import os
    import shutil
    import fitz  # PyMuPDF，用於處理 PDF
    from PIL import Image
    import numpy as np
    import cv2
    from paddleocr import PaddleOCR

    os.makedirs(output_folder, exist_ok=True)
    
    # 專案根目錄
    base_dir = os.path.dirname(os.path.abspath(output_folder))
    
    # image 輸出目錄
    image_output_folder = os.path.join(base_dir, "image")
    os.makedirs(image_output_folder, exist_ok=True)

    ocr = PaddleOCR(use_angle_cls=True, lang='ch')

    for file in os.listdir(input_folder):
        file_lower = file.lower()
        # 判斷是否為支援的格式
        if not file_lower.endswith(('.jpg', '.png', '.jpeg', '.tiff', '.bmp', '.pdf')):
            continue

        file_path = os.path.join(input_folder, file)
        print(f"Processing: {file_path}")
        
        # 移除副檔名，準備檔名
        txt_file_name, _ = os.path.splitext(file)
        output_text_path = os.path.join(output_folder, txt_file_name + ".txt")
        
        all_text_results = [] # 用來儲存此檔案所有頁面的文字

        # --- 分流處理：如果是 PDF ---
        if file_lower.endswith('.pdf'):
            try:
                # 複製 PDF 原檔到 image 資料夾 (備份用)
                shutil.copy2(file_path, os.path.join(image_output_folder, file))

                # 使用 PyMuPDF 開啟 PDF
                doc = fitz.open(file_path)
                
                for page_num, page in enumerate(doc):
                    # 將 PDF 頁面轉為圖片 (zoom=2 代表放大兩倍以提高 OCR 準確度)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    
                    # 將 pixmap 轉為圖片格式供 OCR 使用
                    img_data =  np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                    
                    # 如果是 RGBA，轉為 RGB
                    if pix.n == 4:
                        img_data = cv2.cvtColor(img_data, cv2.COLOR_RGBA2RGB)
                    elif pix.n == 3:
                        # PyMuPDF 預設是 RGB，但在某些 OpenCV 環境下可能需要轉 BGR (PaddleOCR 接受 RGB)
                        pass 

                    # 執行 OCR (傳入 numpy array)
                    result = ocr.ocr(img_data, cls=True)
                    
                    # 處理當頁結果
                    page_text = parse_ocr_result(result)
                    all_text_results.append(f"--- Page {page_num + 1} ---\n{page_text}")
                
                doc.close()

            except Exception as e:
                print(f"Error processing PDF {file}: {e}")
                continue

        # --- 分流處理：如果是圖片 ---
        else:
            # 複製圖片
            dest_image_path = os.path.join(image_output_folder, file)
            shutil.copy2(file_path, dest_image_path)

            # 執行 OCR
            result = ocr.ocr(file_path, cls=True)
            text_content = parse_ocr_result(result)
            all_text_results.append(text_content)

        # --- 寫入文字檔 ---
        if all_text_results:
            with open(output_text_path, "w", encoding="utf-8") as out:
                out.write("\n".join(all_text_results))
            print(f"Saved: {output_text_path}")

def parse_ocr_result(result):
    text_buffer = []
    
    # 狀況 1: 如果 result 是 None (沒抓到任何字)
    if result is None:
        return ""

    # 狀況 2: 處理 PaddleOCR 的多層 List 結構
    # 標準結構通常是 [ [line1, line2, ...] ] (Batch 模式)
    # 但有時可能是 [ line1, line2, ... ] (直接列表)
    
    #我們先試著取得「頁面層級」的資料
    # 如果 result[0] 是一個 list，且 result[0][0] 也是一個 list (代表 box 座標)，
    # 那 result 本身就是 list of lines。否則 result[0] 才是 list of lines。
    
    lines = []
    try:
        if isinstance(result, list) and len(result) > 0:
            # 判斷第一層元素是否為 None (空頁面)
            if result[0] is None:
                return ""
            
            # 判斷結構深度
            first_item = result[0]
            if isinstance(first_item, list) and len(first_item) > 0:
                # 檢查 first_item[0] 是否是座標 (list/int)，如果是，那 first_item 就是一條線 (Line)
                # 這代表 result 本身就是 lines 的列表
                if isinstance(first_item[0], (list, tuple)) and len(first_item[0]) == 4:
                     lines = result
                else:
                    # 否則 result[0] 是一頁 (Page)，裡面包含 lines
                    lines = result[0]
    except Exception:
        # 如果結構判斷出錯，回傳空字串避免當機
        return ""

    # 開始解析每一行
    for line in lines:
        # line 的結構預期是 [ [box座標], ("文字", 分數) ]
        try:
            if not isinstance(line, list) or len(line) < 2:
                continue
            
            # line[1] 應該是 ("文字", 分數)
            text_info = line[1]
            
            if isinstance(text_info, (list, tuple)) and len(text_info) > 0:
                text = text_info[0] # 取得文字部分
                
                # 強制轉為字串 (str)，這一步能徹底解決 float found 的錯誤
                text_buffer.append(str(text))
                
        except Exception:
            continue
            
    return "\n".join(text_buffer)

if __name__ == "__main__":
    input_folder = "C:/Users/joerr/Desktop/Receipts1"       # 收據圖片資料夾
    output_folder = "C:/Users/joerr/Desktop/ocr project/txt"   # 輸出資料夾
    batch_ocr(input_folder, output_folder)