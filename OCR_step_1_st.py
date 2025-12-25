import os
import shutil
import fitz
import numpy as np
import cv2

def parse_ocr_result(result):

    
    text_buffer = []
    if result is None: return ""
    lines = []
    try:
        if isinstance(result, list) and len(result) > 0:
            if result[0] is None: return ""
            first_item = result[0]
            if isinstance(first_item, list) and len(first_item) > 0:
                if isinstance(first_item[0], (list, tuple)) and len(first_item[0]) == 4:
                     lines = result
                else:
                    lines = result[0]
    except: return ""
    for line in lines:
        try:
            text = line[1][0]
            text_buffer.append(str(text))
        except: continue
    return "\n".join(text_buffer)

def process_file_ocr(ocr_model, uploaded_file):
    """處理單一檔案的 OCR"""
    if uploaded_file is None:
        return ""

    file_bytes = uploaded_file.read()
    if not file_bytes:
        return ""

    if uploaded_file.name.lower().endswith(".pdf"):
        all_text = []
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)

            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)

            result = ocr_model.ocr(img, cls=True)
            all_text.append(parse_ocr_result(result))

        return "\n".join(all_text)

    else:
        img = cv2.imdecode(
            np.frombuffer(file_bytes, np.uint8),
            cv2.IMREAD_COLOR
        )

        if img is None:
            return ""

        result = ocr_model.ocr(img, cls=True)
        return parse_ocr_result(result)