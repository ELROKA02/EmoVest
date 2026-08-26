"""Pure MetaTrader 5 HTML report decoder and normalizer.

The parser deliberately has no database dependency: preview and commit can parse the
same bytes and compare their fingerprint before any durable write.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException


MAX_REPORT_BYTES = 10 * 1024 * 1024
MAX_REPORT_ROWS = 100_000
ZERO = Decimal("0")


ALIASES = {
    "time": {"time", "hora", "fecha", "fecha hora"},
    "deal": {"deal", "operacion", "ticket"},
    "position": {"position", "posicion", "position id", "id posicion"},
    "symbol": {"symbol", "simbolo", "activo"},
    "type": {"type", "tipo"},
    "direction": {"direction", "direccion", "entry"},
    "volume": {"volume", "volumen", "cantidad"},
    "price": {"price", "precio"},
    "commission": {"commission", "comision"},
    "fee": {"fee", "tasa"},
    "swap": {"swap"},
    "profit": {"profit", "beneficio", "resultado"},
    "comment": {"comment", "comentario"},
}


def _key(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text.replace("\xa0", " ").strip().lower())


ALIAS_LOOKUP = {alias: canonical for canonical, aliases in ALIASES.items() for alias in aliases}


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self.text: list[str] = []
        self.row_count = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if data.strip():
            self.text.append(data.strip())
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell).replace("\xa0", " ")).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if any(self._row):
                self.row_count += 1
                if self.row_count > MAX_REPORT_ROWS:
                    raise ValueError("El informe supera las 100.000 filas HTML")
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None


def decode_report(raw: bytes) -> tuple[str, str]:
    if not raw:
        raise HTTPException(status_code=422, detail="El informe está vacío")
    if len(raw) > MAX_REPORT_BYTES:
        raise HTTPException(status_code=413, detail="El informe supera el límite de 10 MiB")
    encodings = []
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")) or raw[:200].count(b"\x00") > 20:
        encodings.extend(["utf-16", "utf-16-le", "utf-16-be"])
    encodings.extend(["utf-8-sig", "cp1252"])
    for encoding in encodings:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=422, detail="No se reconoce la codificación del informe")


def _decimal(value: str | None) -> Decimal:
    text = (value or "").strip().replace("\xa0", "").replace(" ", "").replace("−", "-")
    if not text or text in {"-", "--"}:
        return ZERO
    text = re.sub(r"[^0-9,\.\-+]", "", text)
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        result = Decimal(text)
    except InvalidOperation as error:
        raise ValueError(f"decimal inválido: {value}") from error
    if not result.is_finite():
        raise ValueError(f"decimal no finito: {value}")
    return result


def _timestamp(value: str, zone: ZoneInfo) -> datetime:
    normalized = value.strip().replace("/", ".").replace("-", ".")
    formats = (
        "%Y.%m.%d %H:%M:%S.%f",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
    )
    for date_format in formats:
        try:
            local = datetime.strptime(normalized, date_format).replace(tzinfo=zone)
            return local.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            continue
    raise ValueError(f"fecha inválida: {value}")


def _find_deals_table(tables: list[list[list[str]]]):
    best = None
    for table in tables:
        for index, row in enumerate(table):
            headers = [ALIAS_LOOKUP.get(_key(cell)) for cell in row]
            score = sum(name in headers for name in ("time", "deal", "symbol", "type", "volume"))
            if score >= 4 and "time" in headers and "deal" in headers:
                if best is None or score > best[0]:
                    best = (score, table, index, headers)
    if best is None:
        raise HTTPException(status_code=422, detail="No se encontró la tabla Deals de MetaTrader 5")
    return best[1], best[2], best[3]


def _metadata(full_text: str) -> tuple[str, str | None]:
    account_match = re.search(r"(?:Account|Cuenta)\s*[:#]?\s*([0-9]{3,})", full_text, re.I)
    broker_match = re.search(r"(?:Company|Broker|Empresa)\s*:\s*([^\n|]{2,120})", full_text, re.I)
    account = account_match.group(1) if account_match else "unknown"
    broker = broker_match.group(1).strip() if broker_match else None
    return account, broker


def _movement_type(row_type: str, amount: Decimal) -> str | None:
    kind = _key(row_type)
    if any(word in kind for word in ("balance", "deposit", "deposito", "ingreso")):
        return "DEPOSIT" if amount >= 0 else "WITHDRAWAL"
    if any(word in kind for word in ("withdraw", "retiro")):
        return "WITHDRAWAL"
    if "commission" in kind or "comision" in kind:
        return "COMMISSION"
    if "fee" in kind or "tasa" in kind:
        return "FEE"
    if any(word in kind for word in ("credit", "credito", "adjust", "ajuste")):
        return "ADJUSTMENT"
    return None


def parse_mt5_report(raw: bytes, timezone_name: str, resolutions: list[dict] | None = None) -> dict:
    try:
        zone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as error:
        raise HTTPException(status_code=422, detail="La zona horaria IANA no es válida") from error

    html, encoding = decode_report(raw)
    parser = _TableParser()
    try:
        parser.feed(html)
    except ValueError as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    table, header_index, headers = _find_deals_table(parser.tables)
    account, broker = _metadata("\n".join(parser.text))
    if account == "unknown":
        raise HTTPException(status_code=422, detail="No se encontró la cuenta de origen en el informe MT5")
    account_hash = hashlib.sha256(f"{broker or ''}|{account}".encode()).hexdigest()
    fingerprint = hashlib.sha256(raw).hexdigest()
    normalized_rows = []
    errors = []

    seen_deals = set()
    for number, cells in enumerate(table[header_index + 1 :], start=header_index + 2):
        if len(normalized_rows) >= MAX_REPORT_ROWS:
            raise HTTPException(status_code=413, detail="El informe supera las 100.000 filas")
        values = {name: cells[index] if index < len(cells) else "" for index, name in enumerate(headers) if name}
        if not values.get("time") or not values.get("deal"):
            continue
        try:
            when = _timestamp(values["time"], zone)
            deal = values["deal"].strip()
            if deal in seen_deals:
                errors.append({"row": number, "error": f"Deal duplicado dentro del informe: {deal}"})
                continue
            seen_deals.add(deal)
            source_key = hashlib.sha256(f"METATRADER5|{account_hash}|{deal}".encode()).hexdigest()
            normalized_rows.append({
                "row": number,
                "deal": deal,
                "source_key": source_key,
                "time": when.isoformat(),
                "position": values.get("position", "").strip(),
                "symbol": values.get("symbol", "").strip(),
                "type": _key(values.get("type", "")),
                "direction": _key(values.get("direction", "")),
                "volume": str(_decimal(values.get("volume"))),
                "price": str(_decimal(values.get("price"))),
                "commission": str(_decimal(values.get("commission"))),
                "fee": str(_decimal(values.get("fee"))),
                "swap": str(_decimal(values.get("swap"))),
                "profit": str(_decimal(values.get("profit"))),
                "comment": values.get("comment", "").strip(),
            })
        except ValueError as error:
            errors.append({"row": number, "error": str(error)})

    movements = []
    trade_rows = []
    for row in normalized_rows:
        amount = _decimal(row["profit"]) + _decimal(row["commission"]) + _decimal(row["fee"]) + _decimal(row["swap"])
        movement_type = _movement_type(row["type"], amount)
        if movement_type and not row["position"]:
            movements.append({
                "source_rows": [row["source_key"]],
                "row": row["row"],
                "deal": row["deal"],
                "fecha_hora": row["time"],
                "tipo": movement_type,
                "importe": str(amount),
                "descripcion": row["comment"] or row["type"],
            })
        elif row["symbol"]:
            if _decimal(row["volume"]) <= 0 or _decimal(row["price"]) <= 0:
                errors.append({"row": row["row"], "error": "Un deal de trading necesita volumen y precio positivos"})
            else:
                trade_rows.append(row)

    resolution_keys = [
        key
        for resolution in (resolutions or [])
        for key in [*(resolution.get("entries") or []), *(resolution.get("exits") or [])]
    ]
    resolved_keys = set(resolution_keys)
    grouped = defaultdict(list)
    for row in trade_rows:
        if row["source_key"] in resolved_keys:
            continue
        if row["position"]:
            grouped[row["position"]].append(row)

    proposed = []
    skipped_open = []
    conflicts = []
    if len(resolved_keys) != len(resolution_keys):
        conflicts.append({"reason": "Una fila no puede pertenecer a más de un grupo manual"})
    for row in trade_rows:
        if not row["position"] and row["source_key"] not in resolved_keys:
            conflicts.append({
                "row": row["row"],
                "deal": row["deal"],
                "source_key": row["source_key"],
                "reason": "Deal sin Position: necesita agrupación manual",
            })
    for position, rows in grouped.items():
        rows.sort(key=lambda item: (item["time"], item["row"]))
        entries, exits = [], []
        open_quantity = ZERO
        side = None
        ambiguous = False
        for row in rows:
            quantity = _decimal(row["volume"])
            direction = row["direction"].replace(" ", "_")
            if direction in {"in", "entrada"}:
                row_side = "LONG" if "buy" in row["type"] or "compra" in row["type"] else "SHORT"
                if side and side != row_side and open_quantity > ZERO:
                    ambiguous = True
                side = side or row_side
                open_quantity += quantity
                entries.append(row)
            elif direction in {"out", "salida", "out_by", "salida_por"}:
                open_quantity -= quantity
                exits.append(row)
            elif direction in {"in/out", "inout", "entrada/salida"}:
                closed = min(open_quantity, quantity)
                if closed:
                    exit_leg = dict(row, volume=str(closed), source_leg="EXIT")
                    exits.append(exit_leg)
                    open_quantity -= closed
                remainder = quantity - closed
                if remainder:
                    ambiguous = True
            else:
                conflicts.append({"position": position, "row": row["row"], "reason": "Dirección MT5 desconocida"})
                ambiguous = True

        entered = sum((_decimal(item["volume"]) for item in entries), ZERO)
        exited = sum((_decimal(item["volume"]) for item in exits), ZERO)
        if ambiguous or entered <= 0 or exited > entered:
            conflicts.append({"position": position, "reason": "La posición requiere agrupación manual"})
            continue
        if open_quantity > Decimal("0.000001"):
            skipped_open.append({"position": position, "symbol": rows[0]["symbol"], "cantidad_abierta": str(open_quantity)})
            continue

        entry_price = sum((_decimal(item["price"]) * _decimal(item["volume"]) for item in entries), ZERO) / entered
        exit_payload = []
        for item in exits:
            net = _decimal(item["profit"]) + _decimal(item["commission"]) + _decimal(item["swap"]) + _decimal(item["fee"])
            exit_payload.append({
                "source_key": item["source_key"],
                "source_leg": item.get("source_leg"),
                "fecha_hora": item["time"],
                "cantidad": item["volume"],
                "precio": item["price"],
                "resultado_bruto": item["profit"],
                "impacto_comision": item["commission"],
                "impacto_swap": item["swap"],
                "impacto_tasa": item["fee"],
                "resultado_neto": str(net),
            })
        proposed.append({
            "position": position,
            "activo": rows[0]["symbol"],
            "tipo_operacion": side,
            "fecha_hora": entries[0]["time"],
            "fecha_cierre": exits[-1]["time"],
            "cantidad": str(entered),
            "precio_entrada": str(entry_price),
            "entries": [{
                "source_key": item["source_key"],
                "fecha_hora": item["time"],
                "cantidad": item["volume"],
                "precio": item["price"],
                "impacto_comision": item["commission"],
                "impacto_swap": item["swap"],
                "impacto_tasa": item["fee"],
                "resultado_neto": str(_decimal(item["profit"]) + _decimal(item["commission"]) + _decimal(item["swap"]) + _decimal(item["fee"])),
            } for item in entries],
            "exits": exit_payload,
            "source_rows": [item["source_key"] for item in rows],
        })

    rows_by_key = {row["source_key"]: row for row in trade_rows}
    for index, resolution in enumerate(resolutions or [], start=1):
        entry_keys = resolution.get("entries") or []
        exit_keys = resolution.get("exits") or []
        side = str(resolution.get("tipo_operacion") or "").upper()
        try:
            entries = [rows_by_key[key] for key in entry_keys]
            exits = [rows_by_key[key] for key in exit_keys]
        except KeyError:
            conflicts.append({"reason": f"La agrupación manual {index} referencia una fila inexistente"})
            continue
        if side not in {"LONG", "SHORT"} or not entries or not exits:
            conflicts.append({"reason": f"La agrupación manual {index} necesita lado, entradas y salidas"})
            continue
        symbols = {row["symbol"] for row in [*entries, *exits]}
        entered = sum((_decimal(row["volume"]) for row in entries), ZERO)
        exited = sum((_decimal(row["volume"]) for row in exits), ZERO)
        if len(symbols) != 1 or entered != exited:
            conflicts.append({"reason": f"La agrupación manual {index} mezcla símbolos o no cierra la cantidad"})
            continue
        entries.sort(key=lambda item: (item["time"], item["row"]))
        exits.sort(key=lambda item: (item["time"], item["row"]))
        entry_price = sum((_decimal(item["price"]) * _decimal(item["volume"]) for item in entries), ZERO) / entered
        proposed.append({
            "position": str(resolution.get("position") or f"manual-{index}"),
            "activo": next(iter(symbols)),
            "tipo_operacion": side,
            "fecha_hora": entries[0]["time"],
            "fecha_cierre": exits[-1]["time"],
            "cantidad": str(entered),
            "precio_entrada": str(entry_price),
            "entries": [{
                "source_key": item["source_key"], "fecha_hora": item["time"],
                "cantidad": item["volume"], "precio": item["price"],
                "impacto_comision": item["commission"], "impacto_swap": item["swap"],
                "impacto_tasa": item["fee"],
                "resultado_neto": str(_decimal(item["profit"]) + _decimal(item["commission"]) + _decimal(item["swap"]) + _decimal(item["fee"])),
            } for item in entries],
            "exits": [{
                "source_key": item["source_key"], "fecha_hora": item["time"],
                "cantidad": item["volume"], "precio": item["price"],
                "resultado_bruto": item["profit"], "impacto_comision": item["commission"],
                "impacto_swap": item["swap"], "impacto_tasa": item["fee"],
                "resultado_neto": str(_decimal(item["profit"]) + _decimal(item["commission"]) + _decimal(item["swap"]) + _decimal(item["fee"])),
            } for item in exits],
            "source_rows": [item["source_key"] for item in [*entries, *exits]],
        })

    return {
        "provider": "METATRADER5",
        "fingerprint": fingerprint,
        "encoding": encoding,
        "account": account,
        "account_hash": account_hash,
        "broker": broker,
        "timezone": timezone_name,
        "normalized_rows": normalized_rows,
        "proposed_operations": proposed,
        "movements": movements,
        "skipped_open": skipped_open,
        "errors": errors,
        "conflicts": conflicts,
    }
