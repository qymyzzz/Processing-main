import io
import os
from datetime import datetime

from dotenv import load_dotenv
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from telegram import Update
from telegram.ext import ContextTypes

from ticket_store import get_tickets

load_dotenv()

SUPPORT_IDS = os.getenv("SUPPORT_IDS").split(",")


def get_role(user_id: int) -> str:
    """Return 'support', 'duty', or 'client'."""
    if str(user_id) in SUPPORT_IDS:
        return "support"
    return "client"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _fmt_ts(ts) -> str:
    if hasattr(ts, "strftime"):
        return ts.strftime("%d.%m.%Y %H:%M")
    return str(ts) if ts else "—"


def _build_excel(tickets: list[dict]) -> bytes:
    wb = Workbook()

    # ── Sheet 1: All tickets ──────────────────────────────────────────────────
    ws = wb.active
    ws.title = "Все тикеты"

    HEADERS = [
        "№ тикета",
        "Чат",
        "Отправитель",
        "Сообщение",
        "Категория",
        "Дата",
        "Статус",
        "Ответ на",
    ]

    # Header row style
    header_fill = PatternFill("solid", start_color="1F4E79")
    header_font = Font(bold=True, color="FFFFFF", name="Arial", size=11)

    for col, h in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )

    ws.row_dimensions[1].height = 30

    # Alternating row colors
    fill_even = PatternFill("solid", start_color="D6E4F0")
    fill_odd = PatternFill("solid", start_color="FFFFFF")
    font_data = Font(name="Arial", size=10)
    red_font = Font(name="Arial", size=10, color="C00000")
    green_font = Font(name="Arial", size=10, color="375623")

    for i, t in enumerate(tickets, 2):
        category = t.get("final_cat") or t.get("ai_cat") or t.get("rule_cat") or "—"
        reply_text = (
            (t.get("reply_to") or {}).get("text", "")[:100]
            if t.get("reply_to")
            else "—"
        )
        status = "✅ Закрыт" if t["resolved"] else "🔴 Открыт"

        row = [
            t["ticket_id"],
            t.get("chat_title", "—"),
            t["sender"],
            t["text"],
            category,
            _fmt_ts(t["timestamp"]),
            status,
            reply_text,
        ]

        fill = fill_even if i % 2 == 0 else fill_odd
        for col, val in enumerate(row, 1):
            cell = ws.cell(row=i, column=col, value=val)
            cell.fill = fill
            cell.font = font_data
            cell.alignment = Alignment(vertical="top", wrap_text=True)

        # Color status cell
        status_cell = ws.cell(row=i, column=7)
        status_cell.font = green_font if t["resolved"] else red_font

    # Column widths
    widths = [10, 20, 20, 50, 18, 18, 14, 40]
    for col, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = w

    ws.freeze_panes = "A2"

    # ── Sheet 2: Summary ──────────────────────────────────────────────────────
    ws2 = wb.create_sheet("Сводка")

    total = len(tickets)
    open_ = sum(1 for t in tickets if not t["resolved"])
    closed = total - open_

    # Gather per-chat stats
    chats: dict[str, dict] = {}
    for t in tickets:
        title = t.get("chat_title", str(t["chat_id"]))
        if title not in chats:
            chats[title] = {"total": 0, "open": 0, "closed": 0}
        chats[title]["total"] += 1
        if t["resolved"]:
            chats[title]["closed"] += 1
        else:
            chats[title]["open"] += 1

    # Gather per-category stats
    cats: dict[str, int] = {}
    for t in tickets:
        cat = t.get("final_cat") or t.get("ai_cat") or t.get("rule_cat") or "—"
        cats[cat] = cats.get(cat, 0) + 1

    title_font = Font(bold=True, name="Arial", size=12, color="1F4E79")
    label_font = Font(bold=True, name="Arial", size=10)
    value_font = Font(name="Arial", size=10)
    sub_fill = PatternFill("solid", start_color="BDD7EE")

    generated = datetime.now().strftime("%d.%m.%Y %H:%M")

    ws2["A1"] = "📊 Сводный отчёт по тикетам"
    ws2["A1"].font = Font(bold=True, name="Arial", size=14, color="1F4E79")
    ws2["A2"] = f"Сформирован: {generated}"
    ws2["A2"].font = Font(name="Arial", size=9, italic=True, color="808080")

    summary_rows = [
        ("", ""),
        ("Всего тикетов", f"=Тикеты!A{total+1}-Тикеты!A2+1" if total else total),
        ("Открытых", open_),
        ("Закрытых", closed),
    ]

    # Just use plain values for summary (simpler and reliable)
    plain_summary = [
        ("", ""),
        ("Всего тикетов", total),
        ("Открытых", open_),
        ("Закрытых", closed),
    ]

    for r, (label, val) in enumerate(plain_summary, 3):
        ws2.cell(row=r, column=1, value=label).font = label_font
        cell = ws2.cell(row=r, column=2, value=val)
        cell.font = value_font
        if label == "Открытых":
            cell.font = Font(name="Arial", size=10, color="C00000", bold=True)
        elif label == "Закрытых":
            cell.font = Font(name="Arial", size=10, color="375623", bold=True)

    # Per-chat breakdown
    row = 8
    ws2.cell(row=row, column=1, value="По чатам").font = title_font
    row += 1
    for h, col in [("Чат", 1), ("Всего", 2), ("Открытых", 3), ("Закрытых", 4)]:
        c = ws2.cell(row=row, column=col, value=h)
        c.font = Font(bold=True, name="Arial", size=10, color="FFFFFF")
        c.fill = PatternFill("solid", start_color="1F4E79")
    row += 1
    for title, s in chats.items():
        fill = fill_even if row % 2 == 0 else fill_odd
        for col, val in [(1, title), (2, s["total"]), (3, s["open"]), (4, s["closed"])]:
            c = ws2.cell(row=row, column=col, value=val)
            c.font = value_font
            c.fill = fill
        row += 1

    # Per-category breakdown
    row += 1
    ws2.cell(row=row, column=1, value="По категориям").font = title_font
    row += 1
    for h, col in [("Категория", 1), ("Кол-во", 2)]:
        c = ws2.cell(row=row, column=col, value=h)
        c.font = Font(bold=True, name="Arial", size=10, color="FFFFFF")
        c.fill = PatternFill("solid", start_color="1F4E79")
    row += 1
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        fill = fill_even if row % 2 == 0 else fill_odd
        ws2.cell(row=row, column=1, value=cat).font = value_font
        ws2.cell(row=row, column=1).fill = fill
        ws2.cell(row=row, column=2, value=count).font = value_font
        ws2.cell(row=row, column=2).fill = fill
        row += 1

    ws2.column_dimensions["A"].width = 30
    ws2.column_dimensions["B"].width = 12
    ws2.column_dimensions["C"].width = 12
    ws2.column_dimensions["D"].width = 12

    # ── Save to bytes ─────────────────────────────────────────────────────────
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


# ── Handler ───────────────────────────────────────────────────────────────────


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /report — выгрузить все тикеты в Excel. Только для поддержки.
    Проверку роли делай снаружи (или добавь get_role здесь).
    """
    user_username = update.effective_user.username
    user_id = update.effective_user.id
    if get_role(user_id) != "support":
        await update.message.reply_text("⚠️ У вас нет доступа к этой команде.")
        return
    tickets = get_tickets(sender=user_username)

    if not tickets:
        await update.message.reply_text("📭 Тикетов пока нет — отчёт пуст.")
        return

    await update.message.reply_text("⏳ Формирую отчёт...")

    excel_bytes = _build_excel(tickets)
    filename = f"tickets_{datetime.now().strftime('%d-%m-%Y_%H-%M')}.xlsx"

    await update.message.reply_document(
        document=io.BytesIO(excel_bytes),
        filename=filename,
        caption=(
            f"📊 *Отчёт по тикетам*\n"
            f"Всего: *{len(tickets)}* · "
            f"Открытых: *{sum(1 for t in tickets if not t['resolved'])}* · "
            f"Закрытых: *{sum(1 for t in tickets if t['resolved'])}*"
        ),
        parse_mode="Markdown",
    )
