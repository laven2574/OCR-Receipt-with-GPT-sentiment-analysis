import os
import fitz
import numpy as np
import cv2
import streamlit as st
import pytesseract

# Windows 本地路徑
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def ocr_image_tesseract(img: np.ndarray) -> str:
    """
    使用 Tesseract 進行 OCR，回傳純文字
    """
    if img is None:
        return ""

    # 基本前處理（對收據很重要）
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    custom_config = r"--oem 3 --psm 6"
    text = pytesseract.image_to_string(
        gray,
        lang="chi_sim+eng+jpn",
        config=custom_config
    )
    return text.strip()


def process_file_ocr(uploaded_file):
    """處理單一檔案的 OCR（Tesseract 版本）"""
    if uploaded_file is None:
        return ""

    file_bytes = uploaded_file.read()
    if not file_bytes:
        return ""

    # PDF
    if uploaded_file.name.lower().endswith(".pdf"):
        all_text = []
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.h, pix.w, pix.n
            )

            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)

            text = ocr_image_tesseract(img)
            if text:
                all_text.append(text)

        return "\n".join(all_text)

    # Image
    else:
        img = cv2.imdecode(
            np.frombuffer(file_bytes, np.uint8),
            cv2.IMREAD_COLOR
        )

        if img is None:
            return ""

        return ocr_image_tesseract(img)
    