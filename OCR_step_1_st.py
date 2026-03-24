import base64
import fitz
import numpy as np
import cv2
import streamlit as st
from openai import OpenAI


# -------------------------------------------------
# Vision OCR via GPT-4o (replaces Tesseract)
# -------------------------------------------------

def encode_image_to_base64(img: np.ndarray) -> str:
    """將 OpenCV ndarray 編碼為 base64 JPEG 字串"""
    _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return base64.b64encode(buffer).decode("utf-8")


def ocr_image_gpt4o(img: np.ndarray, client: OpenAI) -> str:
    """
    使用 GPT-4o Vision 對單張圖片做 OCR。
    直接傳圖片，無需任何前處理或幾何校正，
    模型可自動處理角度、模糊及多語言（中/英/日）。
    """
    if img is None:
        return ""

    b64 = encode_image_to_base64(img)

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "請完整抽取這張收據圖片中的所有文字，"
                            "保留原有排版與換行，不要翻譯或總結，"
                            "只需輸出原始文字內容。"
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ]
    )

    return response.choices[0].message.content.strip()


def process_file_ocr(uploaded_file) -> str:
    """
    處理單一檔案的 OCR（GPT-4o Vision 版本）。
    支援 PDF（逐頁處理）及常見圖片格式（JPG / PNG）。
    """
    if uploaded_file is None:
        return ""

    api_key = st.secrets.get("OPENAI_API_KEY")
    client  = OpenAI(api_key=api_key)

    file_bytes = uploaded_file.read()
    if not file_bytes:
        return ""

    # ── PDF ──────────────────────────────────────────
    if uploaded_file.name.lower().endswith(".pdf"):
        all_text = []
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        for page_num, page in enumerate(doc):
            # 以 2x 解析度渲染，保留細節
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.h, pix.w, pix.n
            )

            # RGBA → RGB
            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)

            text = ocr_image_gpt4o(img, client)
            if text:
                all_text.append(text)

        return "\n".join(all_text)

    # ── Image ────────────────────────────────────────
    else:
        img = cv2.imdecode(
            np.frombuffer(file_bytes, np.uint8),
            cv2.IMREAD_COLOR
        )

        if img is None:
            return ""

        return ocr_image_gpt4o(img, client)