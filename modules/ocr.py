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

    # 1. Сумма — ищем ТОЛЬКО ключевые слова: ИТОГ, ИТОГО, К ОПЛАТЕ, НАЛИЧНЫМИ, ОПЛАЧЕНО
    total_keywords = [
        r"итого\s*[:=]?\s*(\d+[.,]\d{2})",
        r"итог\s*[:=]?\s*(\d+[.,]\d{2})",
        r"к\s*оплате\s*[:=]?\s*(\d+[.,]\d{2})",
        r"оплачено\s*[:=]?\s*(\d+[.,]\d{2})",
        r"получено\s*[:=]?\s*(\d+[.,]\d{2})",
        r"итоговая\s*сумма\s*[:=]?\s*(\d+[.,]\d{2})",
        r"сумма\s*без\s*ндс\s*[:=]?\s*(\d+[.,]\d{2})",
        r"наличными\s*[:=]?\s*=?\s*(\d+[.,]\d{2})",
        r"итого\s*[:=]?\s*=?\s*(\d+[.,]\d{2})",
        r"итог\s*[:=]?\s*=?\s*(\d+[.,]\d{2})",
        r"=(\d{3,6}[.,]\d{2})",
    ]

    candidates = []
    for pattern in total_keywords:
        for line in lines:
            for m in re.finditer(pattern, line.lower()):
                try:
                    raw_num = m.group(1).strip().replace(",", ".")
                    val = float(raw_num)
                    if 10 < val < 10_000_000:
                        candidates.append(val)
                except Exception:
                    pass

    if candidates:
        # Берём максимальное — обычно это ИТОГ
        result["amount"] = int(round(max(candidates)))
    else:
        # Fallback: самое большое число с копейками (\d+.\d{2})
        all_nums = []
        for line in lines:
            for m in re.finditer(r"(\d{2,6}[.,]\d{2})", line):
                try:
                    val = float(m.group(1).replace(",", "."))
                    if 10 < val < 10_000_000:
                        all_nums.append(val)
                except Exception:
                    pass
        if all_nums:
            result["amount"] = int(round(max(all_nums)))

    # 2. Магазин — ищем «ИП», «ООО», или берём первую осмысленную строку
    shop_patterns = [r"^(ИП\s+.+)", r"^(ООО\s+.+)", r"^(АО\s+.+)"]
    for pattern in shop_patterns:
        for line in lines:
            m = re.search(pattern, line, re.IGNORECASE)
            if m:
                result["shop"] = m.group(1)[:60]
                break
        if result["shop"]:
            break

    if not result["shop"] and lines:
        # Берём первую строку с буквами (не цифры)
        for line in lines[:5]:
            if re.search(r"[А-Яа-яA-Za-z]{3,}", line):
                result["shop"] = line[:60]
                break

    # 3. Дата
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


def parse_receipt_items(text: str) -> list:
    """Извлекает позиции товаров из текста чека."""
    items = []
    if not text:
        return items

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Стоп-слова — не названия и не позиции
    stop_words = [
        "ндс", "не облагается", "номер продажи", "кассир", "итог", "сумма",
        "наличными", "получено", "место расчетов", "инн", "ккт", "фн",
        "фд", "фп", "смена", "кассовый чек", "онлайн - касса", "рии",
        "адрес", "ул ", "г. ", "зн ", "рн ", "рихпд",
    ]

    def is_stop(line_low):
        return any(w in line_low for w in stop_words)

    def is_name(line, line_low):
        # Название — есть буквы. Цифры допустимы (артикулы, размеры)
        if is_stop(line_low):
            return False
        # Если есть формат суммы (X.XX*N или =X.XX) — это НЕ название
        if re.search(r"\d+[.,]\d{2}", line):
            return False
        letters = sum(c.isalpha() for c in line)
        return letters >= 3

    def extract_amount(line):
        # Формат «цена*кол-во» или «кол-во x цена=сумма»
        # Пример: «5.000 x 19.80=99.00» — 5.000 * 19.80 = 99.00
        m = re.search(r"(\d+[.,]?\d*)\s*[*x]\s*(\d+[.,]?\d*)", line)
        if m:
            n1 = float(m.group(1).replace(",", "."))
            n2 = float(m.group(2).replace(",", "."))
            # Если n1 < n2 — это (кол-во × цена)
            if n1 < n2:
                qty, price = n1, n2
            else:
                price, qty = n1, n2
            return price, qty, price * qty, True
        # Формат «=сумма»
        m = re.search(r"=+\s*(\d+[.,]\d{2})", line)
        if m:
            total = float(m.group(1).replace(",", "."))
            return total, 1, total, False
        return None, None, None, False

    pending_name = None

    for line in lines:
        line_low = line.lower()

        if is_stop(line_low):
            continue

        # Если есть сумма — создаём позицию
        price, qty, total, has_qty = extract_amount(line)
        if price is not None and 10 < total < 10_000_000:
            name = pending_name or "позиция"
            items.append({
                "name": name[:80],
                "qty": qty,
                "price": price,
                "total": total,
            })
            pending_name = None
            continue

        # Если название — запоминаем
        if is_name(line, line_low):
            pending_name = line

    return items
