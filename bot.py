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


def font(size, bold=False, serif=False):
    if serif:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_invitation(guest):
    # invitation_template.png is the FINAL approved LFH design.
    # Only the [Invitee Name] field is replaced; all other text/design stays unchanged.
    img = Image.open(TEMPLATE).convert("RGB")
    draw = ImageDraw.Draw(img)
    width, height = img.size
    blue = (18, 63, 134)

    # Approved template is 1024 x 1536. Scale coordinates if the template changes size.
    sx, sy = width / 1024, height / 1536
    name_box = (int(175 * sx), int(490 * sy), int(849 * sx), int(570 * sy))
    underline_y = int(560 * sy)

    # Remove the placeholder name and its original underline.
    draw.rectangle(name_box, fill="white")

    # Bold serif styling to match the approved [Invitee Name] text.
    size = max(24, int(width * 0.040))
    f = font(size, bold=True, serif=True)
    text = guest.strip()
    max_width = int(width * 0.70)

    bbox = draw.textbbox((0, 0), text, font=f)
    text_width = bbox[2] - bbox[0]
    if text_width > max_width:
        size = max(20, int(size * max_width / text_width))
        f = font(size, bold=True, serif=True)
        bbox = draw.textbbox((0, 0), text, font=f)
        text_width = bbox[2] - bbox[0]

    text_height = bbox[3] - bbox[1]
    box_top, box_bottom = name_box[1], name_box[3]
    x = (width - text_width) / 2
    y = box_top + (box_bottom - box_top - text_height) / 2 - bbox[1] - 2
    draw.text((x, y), text, font=f, fill=blue)

    # Clean centered underline beneath the guest name.
    line_width = min(max(text_width + int(width * 0.07), int(width * 0.25)), int(width * 0.70))
    line_x1 = (width - line_width) / 2
    line_x2 = line_x1 + line_width
    draw.line((line_x1, underline_y, line_x2, underline_y), fill=blue, width=max(2, int(width / 340)))

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
