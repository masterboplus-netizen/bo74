"""OCR для чеков через OCR.space (бесплатный API)."""
import os
import json
import re
import urllib.request

OCR_API_KEY = os.getenv("OCR_SPACE_API_KEY", "")
OCR_URL = "https://api.ocr.space/parse/image"


def ocr_image(image_bytes: bytes, language: str = "rus") -> dict:
    """Отправляет фото в OCR.space, возвращает {ok, text, error}."""
    if not OCR_API_KEY:
        return {"ok": False, "error": "OCR_SPACE_API_KEY не задан в Secrets"}

    boundary = "----BoBoundary7MA4YWxkTrZu0gW"
    CRLF = b"\r\n"

    body = b""
    # apikey
    body += ("--" + boundary + "\r\n").encode()
    body += b'Content-Disposition: form-data; name="apikey"\r\n\r\n'
    body += OCR_API_KEY.encode() + CRLF
    # language
    body += ("--" + boundary + "\r\n").encode()
    body += b'Content-Disposition: form-data; name="language"\r\n\r\n'
    body += language.encode() + CRLF
    # isOverlayRequired
    body += ("--" + boundary + "\r\n").encode()
    body += b'Content-Disposition: form-data; name="isOverlayRequired"\r\n\r\n'
    body += b"false" + CRLF
    # OCREngine
    body += ("--" + boundary + "\r\n").encode()
    body += b'Content-Disposition: form-data; name="OCREngine"\r\n\r\n'
    body += b"2" + CRLF
    # file
    body += ("--" + boundary + "\r\n").encode()
    body += b'Content-Disposition: form-data; name="file"; filename="receipt.jpg"\r\n'
    body += b"Content-Type: image/jpeg\r\n\r\n"
    body += image_bytes + CRLF
    # final
    body += ("--" + boundary + "--\r\n").encode()

    req = urllib.request.Request(OCR_URL, data=body)
    req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": "HTTP: " + str(e)}

    if data.get("IsErroredOnProcessing"):
        err = data.get("ErrorMessage", "unknown")
        if isinstance(err, list):
            err = "; ".join(err)
        return {"ok": False, "error": err}

    parsed = data.get("ParsedResults", [])
    if not parsed:
        return {"ok": False, "error": "Пустой результат"}

    text = parsed[0].get("ParsedText", "")
    return {"ok": True, "text": text}


def parse_receipt(text: str) -> dict:
    """Из текста чека вытаскивает сумму, магазин, дату."""
    result = {"amount": None, "shop": None, "date": None, "raw": text}

    if not text:
        return result

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # 1. Сумма — ищем «Итого», «ИТОГ», «К оплате», «Сумма»
    amount_patterns = [
        r"(?:итого|итог|к оплате|сумма|всего)[:\s]*([\d\s]+[.,]?\d*)\s*(?:руб|₽|р\.)?",
        r"([\d\s]+[.,]\d{2})\s*(?:руб|₽)",
        r"(\d{3,6})[.,]\d{2}",
    ]
    for pattern in amount_patterns:
        for line in lines:
            m = re.search(pattern, line.lower())
            if m:
                try:
                    # Сохраняем точку/запятую для копеек
                    raw_num = m.group(1).strip().replace(" ", "").replace(",", ".")
                    try:
                        val = float(raw_num)
                        if 10 < val < 10000000:
                            result["amount"] = int(round(val))
                            break
                    except Exception:
                        pass
                except Exception:
                    pass
        if result["amount"]:
            break

    # 2. Магазин — первая непустая строка
    if lines:
        result["shop"] = lines[0][:60]

    # 3. Дата — dd.mm.yyyy
    date_pattern = r"(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})"
    for line in lines:
        m = re.search(date_pattern, line)
        if m:
            d, mo, y = m.group(1), m.group(2), m.group(3)
            if len(y) == 2:
                y = "20" + y
            result["date"] = y + "-" + mo.zfill(2) + "-" + d.zfill(2)
            break

    return result
