"""OCR для чеков через OCR.space."""
import os
import json
import re
import time
import urllib.request

OCR_API_KEY = os.getenv("OCR_SPACE_API_KEY", "")
OCR_URL = "https://api.ocr.space/parse/image"


def ocr_image(image_bytes, language="rus"):
    if not OCR_API_KEY:
        return {"ok": False, "error": "OCR_SPACE_API_KEY не задан"}
    boundary = "----BoBoundary7MA4YWxkTrZu0gW"
    CRLF = b"\r\n"
    body = b""
    body += ("--" + boundary + "\r\n").encode()
    body += b'Content-Disposition: form-data; name="apikey"\r\n\r\n'
    body += OCR_API_KEY.encode() + CRLF
    body += ("--" + boundary + "\r\n").encode()
    body += b'Content-Disposition: form-data; name="language"\r\n\r\n'
    body += language.encode() + CRLF
    body += ("--" + boundary + "\r\n").encode()
    body += b'Content-Disposition: form-data; name="isOverlayRequired"\r\n\r\n'
    body += b"false" + CRLF
    body += ("--" + boundary + "\r\n").encode()
    body += b'Content-Disposition: form-data; name="OCREngine"\r\n\r\n'
    body += b"3" + CRLF
    body += ("--" + boundary + "\r\n").encode()
    body += b'Content-Disposition: form-data; name="scale"\r\n\r\n'
    body += b"true" + CRLF
    body += ("--" + boundary + "\r\n").encode()
    body += b'Content-Disposition: form-data; name="file"; filename="receipt.jpg"\r\n'
    body += b"Content-Type: image/jpeg\r\n\r\n"
    body += image_bytes + CRLF
    body += ("--" + boundary + "--\r\n").encode()
    last_error = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(OCR_URL, data=body)
            req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("IsErroredOnProcessing"):
                err = data.get("ErrorMessage", "unknown")
                if isinstance(err, list):
                    err = "; ".join(err)
                if "E502" in err or "E503" in err or "timeout" in err.lower():
                    last_error = err
                    time.sleep(2)
                    continue
                return {"ok": False, "error": err}
            parsed = data.get("ParsedResults", [])
            if not parsed:
                return {"ok": False, "error": "Пустой результат"}
            return {"ok": True, "text": parsed[0].get("ParsedText", "")}
        except Exception as e:
            last_error = "HTTP: " + str(e)
            time.sleep(2)
    return {"ok": False, "error": last_error or "OCR не отвечает"}


def parse_receipt(text):
    """Извлекает сумму, магазин, дату."""
    result = {"amount": None, "shop": None, "date": None, "raw": text}
    if not text:
        return result
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # 1. Сумма — из "ИТОГ / ИТОГО / К ОПЛАТЕ / НАЛИЧНЫМИ / ПОЛУЧЕНО"
    amount_candidates = []
    for i, line in enumerate(lines):
        line_low = line.lower()
        if "ндс" in line_low:
            continue
        if any(w in line_low for w in ["итог", "итого", "к оплате", "оплата", "наличными", "получено"]):
            m = re.search(r"=+\s*(\d+[.,]\d{2})", line)
            if m:
                try:
                    val = float(m.group(1).replace(",", "."))
                    if 10 < val < 10_000_000:
                        amount_candidates.append(val)
                except Exception:
                    pass
            else:
                for j in range(i + 1, min(i + 3, len(lines))):
                    m = re.search(r"=+\s*(\d+[.,]\d{2})", lines[j])
                    if m:
                        try:
                            val = float(m.group(1).replace(",", "."))
                            if 10 < val < 10_000_000:
                                amount_candidates.append(val)
                                break
                        except Exception:
                            pass

    if amount_candidates:
        result["amount"] = int(round(max(amount_candidates)))

    # 2. Fallback — =NNNN.NN (только >= 200, чтобы отсечь НДС/скидки)
    if result["amount"] is None:
        all_equal = []
        for i, line in enumerate(lines):
            line_low = line.lower()
            if "ндс" in line_low:
                continue
            if i > 0 and any(w in lines[i-1].lower() for w in ["ндс", "скидка", "сдача", "получено"]):
                continue
            if i < len(lines) - 1 and any(w in lines[i+1].lower() for w in ["ндс", "скидка", "сдача"]):
                continue
            for m in re.finditer(r"=+\s*(\d{3,7}[.,]\d{2})", line):
                try:
                    val = float(m.group(1).replace(",", "."))
                    if 200 <= val < 10_000_000:
                        all_equal.append(val)
                except Exception:
                    pass
        if all_equal:
            result["amount"] = int(round(max(all_equal)))

    # 3. Магазин
    for line in lines[:5]:
        m = re.search(r'^(АО|ООО|ИП|ЗАО|ПАО)\s+[\"«]?(.+?)[\"»]?$', line, re.IGNORECASE)
        if m:
            result["shop"] = (m.group(1) + " " + m.group(2))[:60]
            break
    if not result["shop"]:
        for line in lines[:5]:
            if re.search(r"[А-Яа-яA-Za-z]{3,}", line):
                result["shop"] = line[:60]
                break

    # 4. Дата
    for line in lines:
        m = re.search(r"(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})", line)
        if m:
            d, mo, y = m.group(1), m.group(2), m.group(3)
            if len(y) == 2:
                y = "20" + y
            result["date"] = y + "-" + mo.zfill(2) + "-" + d.zfill(2)
            break

    return result


def parse_receipt_items(text):
    """Позиции из чека."""
    items = []
    if not text:
        return items
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    stop_words = [
        "ндс", "не облагается", "номер продажи", "кассир", "итог", "сумма",
        "наличными", "получено", "место расчетов", "инн", "ккт", "фн",
        "фд", "фп", "смена", "кассовый чек", "онлайн", "рии",
        "адрес", "ул ", "г. ", "зн ", "рн ", "рихпд",
        "приход", "расход", "спасибо", "покупку", "покупка", "ждите",
        "ответ", "смс", "чек", "№", "qr", "сайт", "www", "http",
        "тел", "телефон", "оператор", "касса", "документ",
        "позиций", "покупок", "арт:", "шк:", "код:", "шт.",
        "сдача", "скидка", "кол-во", "цена", "стоим",
        "наименование", "руб",
    ]
    def is_stop(line_low):
        return any(w in line_low for w in stop_words)
    def is_name(line, line_low):
        if is_stop(line_low):
            return False
        if re.search(r"\d+[.,]\d{2}", line):
            return False
        if ":" in line and not re.match(r"^[А-Яа-я]", line):
            return False
        if line.strip().startswith(("«", '"', "'")):
            return False
        letters = sum(c.isalpha() for c in line)
        return letters >= 3
    pending_name = None
    for line in lines:
        line_low = line.lower()
        if is_stop(line_low):
            continue
        m = re.search(r"(\d+[.,]?\d*)\s*[*x]\s*(\d+[.,]?\d*)\s*=?\s*(\d+[.,]\d{2})?", line)
        if m:
            n1 = float(m.group(1).replace(",", "."))
            n2 = float(m.group(2).replace(",", "."))
            if n1 < n2:
                qty, price = n1, n2
            else:
                price, qty = n1, n2
            total = price * qty
            if m.group(3):
                total = float(m.group(3).replace(",", "."))
            name = pending_name or "позиция"
            items.append({"name": name[:80], "qty": qty, "price": price, "total": total})
            pending_name = None
            continue
        m_single = re.match(r"^\s*=?\s*(\d{1,6}[.,]\d{2})\s*$", line)
        if m_single and pending_name:
            try:
                val = float(m_single.group(1).replace(",", "."))
                if 1 < val < 1_000_000:
                    items.append({"name": pending_name[:80], "qty": 1, "price": val, "total": val})
                    pending_name = None
                    continue
            except Exception:
                pass
        if is_name(line, line_low):
            pending_name = line
    if len(items) <= 1:
        return items
    return items
