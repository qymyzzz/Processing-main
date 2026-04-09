from telegram import Update

from ticket_store import get_tickets


async def send_ticket_list(update: Update, tickets: list) -> None:
    if not tickets:
        await update.message.reply_text("📭 В этом чате пока нет тикетов.")
        return

    open_tickets = [t for t in tickets if not t["resolved"]]
    resolved_tickets = [t for t in tickets if t["resolved"]]
    chat_title = tickets[0]["chat_title"]

    lines = [
        f"📋 *Все тикеты — {chat_title}*",
        f"Всего: *{len(open_tickets)}* открытых тикетов",
    ]

    if open_tickets:
        for t in open_tickets:
            lines += _format_ticket(t)
    else:
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "🔴 *ОТКРЫТЫХ ТИКЕТОВ НЕТ*",
            "━━━━━━━━━━━━━━━━━━━━",
        ]

    # if resolved_tickets:
    #     lines += [
    #         "",
    #         "━━━━━━━━━━━━━━━━━━━━",
    #         "✅ *ЗАКРЫТЫЕ ТИКЕТЫ*",
    #         "━━━━━━━━━━━━━━━━━━━━",
    #     ]
    #     for t in resolved_tickets:
    #         lines += _format_ticket(t)

    await _send_in_chunks(update, lines)


def _format_ticket(t: dict) -> list[str]:
    ts = (
        t["timestamp"].strftime("%d.%m.%Y %H:%M")
        if hasattr(t["timestamp"], "strftime")
        else str(t["timestamp"])
    )
    category = t["final_cat"] or t["ai_cat"] or t["rule_cat"] or "—"
    text_preview = t["text"][:200] + ("…" if len(t["text"]) > 200 else "")

    block = [
        "",
        f"🎫 *Тикет #{t['ticket_id']}*",
        f"👤 *От:* {t['sender']}",
        f"🕐 *Время:* {ts}",
        f"🏷 *Категория:* {category}",
        f"💬 *Сообщение:*",
        f"_{text_preview}_",
    ]

    if t.get("reply_to"):
        reply = t["reply_to"]
        reply_preview = reply.get("text", "")[:80] + (
            "…" if len(reply.get("text", "")) > 80 else ""
        )
        block.append(f"↩️ *Ответ на:* _{reply_preview}_")

    return block


async def _send_in_chunks(update: Update, lines: list[str]) -> None:
    chunks, current_lines, current_len = [], [], 0

    for line in lines:
        line_len = len(line) + 1
        if current_len + line_len > 3800 and current_lines:
            chunks.append("\n".join(current_lines))
            current_lines, current_len = [], 0
        current_lines.append(line)
        current_len += line_len

    if current_lines:
        chunks.append("\n".join(current_lines))

    for i, chunk in enumerate(chunks, 1):
        header = f"_часть {i}/{len(chunks)}_\n" if len(chunks) > 1 else ""
        await update.message.reply_text(
            header + chunk,
            parse_mode="Markdown",
        )
