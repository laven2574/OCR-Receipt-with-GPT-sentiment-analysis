import os
import fitz
import numpy as np
import cv2
import streamlit as st
import pytesseract
 
 
# Windows 本地路徑
#pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
#pytesseract.pytesseract.tesseract_cmd = r"/usr/bin/tesseract"
 
 
# -------------------------------------------------
# Geometry Correction Helpers
# -------------------------------------------------
 
def order_points(pts: np.ndarray) -> np.ndarray:
    """將四個角點排列為：左上、右上、右下、左下"""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]    # 左上
    rect[2] = pts[np.argmax(s)]    # 右下
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)] # 右上
    rect[3] = pts[np.argmax(diff)] # 左下
    return rect
 
 
def correct_perspective(img: np.ndarray) -> np.ndarray:
    """
    偵測收據邊界四邊形並做透視校正。
    若找不到明顯的四邊形輪廓，直接返回原圖。
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)
 
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
 
    receipt_contour = None
    for c in contours[:5]:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            receipt_contour = approx
            break
 
    if receipt_contour is None:
        return img  # 找不到四邊形，返回原圖
 
    pts = receipt_contour.reshape(4, 2).astype(np.float32)
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
 
    widthA  = np.linalg.norm(br - bl)
    widthB  = np.linalg.norm(tr - tl)
    maxWidth = int(max(widthA, widthB))
 
    heightA  = np.linalg.norm(tr - br)
    heightB  = np.linalg.norm(tl - bl)
    maxHeight = int(max(heightA, heightB))
 
    dst = np.array(
        [[0, 0], [maxWidth - 1, 0],
         [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]],
        dtype=np.float32
    )
 
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, M, (maxWidth, maxHeight))
    return warped
 
 
def correct_skew(gray: np.ndarray) -> np.ndarray:
    """
    利用 Hough Line Transform 偵測文字傾斜角度並旋轉修正。
    角度小於 0.5° 不處理，避免不必要的插值損耗。
    """
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180,
        threshold=100, minLineLength=100, maxLineGap=10
    )
    if lines is None:
        return gray
 
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 != x1:
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if -45 < angle < 45:
                angles.append(angle)
 
    if not angles:
        return gray
 
    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.5:
        return gray
 
    h, w = gray.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(
        gray, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )
    return rotated
 
 
# -------------------------------------------------
# OCR
# -------------------------------------------------
 
def ocr_image_tesseract(img: np.ndarray) -> str:
    """
    完整前處理流程後使用 Tesseract 進行 OCR：
    1. 透視校正
    2. 灰階轉換
    3. 旋轉（Skew）校正
    4. Otsu 二值化
    """
    if img is None:
        return ""
 
    # ① 透視校正（針對斜拍照片）
    img = correct_perspective(img)
 
    # ② 灰階
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
 
    # ③ 旋轉校正（針對文字傾斜）
    gray = correct_skew(gray)
 
    # ④ Otsu 二值化
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
 
    custom_config = r"--oem 3 --psm 6"
    text = pytesseract.image_to_string(
        gray,
        lang="chi_sim+eng+jpn",
        config=custom_config
    )
    return text.strip()
 
 
def process_file_ocr(uploaded_file) -> str:
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