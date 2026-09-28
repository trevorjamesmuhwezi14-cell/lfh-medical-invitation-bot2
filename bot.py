import os
import io
import logging
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", "10000"))
PUBLIC_URL = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
WEBHOOK_PATH = "telegram-webhook"
TEMPLATE = "invitation_template.png"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def make_invitation(guest):
    img = Image.open(TEMPLATE).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Clear the template's blank invitee-name line.
    draw.rectangle((48, 505, 976, 575), fill="white")

    # Center the invitee name and add a clean underline.
    blue = (18, 63, 134)
    text = guest.strip()
    f = font(32, bold=False)

    max_width = 850
    bbox = draw.textbbox((0, 0), text, font=f)
    text_width = bbox[2] - bbox[0]

    if text_width > max_width:
        f = font(27, bold=False)
        bbox = draw.textbbox((0, 0), text, font=f)
        text_width = bbox[2] - bbox[0]

    # Center horizontally on the 1024px-wide invitation.
    x = (1024 - text_width) / 2
    y = 510
    draw.text((x, y), text, font=f, fill=blue)

    # Underline follows the name and is also centered.
    line_width = min(max(text_width + 70, 250), 850)
    line_x1 = (1024 - line_width) / 2
    line_x2 = line_x1 + line_width
    draw.line((line_x1, 566, line_x2, 566), fill=blue, width=3)

    out = io.BytesIO()
    out.name = "LFH_Medical_Launch_Invitation.jpg"
    img.save(out, format="JPEG", quality=95, optimize=True)
    out.seek(0)
    return out


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("💌 Create Personal Invitation", callback_data="create")]]
    await update.message.reply_text(
        "Welcome to the LFH Medical Launch invitation service.\n\n"
        "Tap the button below, then enter the guest's name exactly as you want it to appear "
        "on the invitation (for example: Dr John Doe).",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "create":
        context.user_data["awaiting_name"] = True
        await q.message.reply_text("Please enter the guest name.\n\nExample: Dr John Doe")


async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_name"):
        await update.message.reply_text("Tap “Create Personal Invitation” to begin.")
        return
    guest = update.message.text.strip()
    if len(guest) < 2 or len(guest) > 80:
        await update.message.reply_text("Please enter a valid guest name (2–80 characters).")
        return
    context.user_data["awaiting_name"] = False
    image = make_invitation(guest)
    await update.message.reply_photo(
        photo=image,
        caption=(f"💌 Personal invitation for {guest}\n\n"
                 "LFH Medical Launch & Community Health Camp\n"
                 "Saturday, 3rd October 2026 • 9:00 AM – 5:00 PM"),
    )


def main():
    if not PUBLIC_URL:
        raise RuntimeError("RENDER_EXTERNAL_URL is missing. Deploy this version as a Render Web Service.")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

    webhook_url = f"{PUBLIC_URL}/{WEBHOOK_PATH}"
    logging.info("Starting LFH invitation bot webhook on port %s", PORT)
    logging.info("Webhook URL: %s", webhook_url)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=webhook_url,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
