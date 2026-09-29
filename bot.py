import os
import io
import logging

from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", "10000"))
PUBLIC_URL = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
WEBHOOK_PATH = "telegram-webhook"

# IMPORTANT:
# invitation_template.png must be the FINAL approved LFH invitation image:
# the version containing "[Invitee Name]" exactly as approved.
TEMPLATE = "invitation_template.png"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def name_font(size):
    """Use a serif bold font matching the approved invitation name style."""
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_invitation(guest):
    """
    Keep the approved invitation artwork completely unchanged.
    Only replace the [Invitee Name] placeholder.
    """
    img = Image.open(TEMPLATE).convert("RGB")
    draw = ImageDraw.Draw(img)

    blue = (18, 63, 134)

    # The approved template is 1024 x 1536.
    # Remove ONLY the [Invitee Name] text area.
    # The final approved template already contains the exact centered wording:
    # “We are pleased to invite you to the Launch and Grand Opening of LFH Medical.”
    # “Then there will be a health camp under the theme:”
    # “Healthy Community, Healthy Nation.”
    # “Your presence will be of great honour!”
    # The existing blue underline and all other artwork are deliberately preserved.
    draw.rectangle((250, 485, 775, 552), fill="white")

    # Fit long names while keeping the same centered name treatment.
    max_width = 760
    size = 44
    text = guest.strip()

    while size >= 28:
        f = name_font(size)
        bbox = draw.textbbox((0, 0), text, font=f)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            break
        size -= 2

    # Center the name on the original 1024 px-wide artwork.
    bbox = draw.textbbox((0, 0), text, font=f)
    text_width = bbox[2] - bbox[0]
    x = (1024 - text_width) / 2
    y = 493

    draw.text((x, y), text, font=f, fill=blue)

    out = io.BytesIO()
    out.name = "LFH_Medical_Launch_Invitation.jpg"
    img.save(out, format="JPEG", quality=95, optimize=True)
    out.seek(0)
    return out


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💌 Create Personal Invitation", callback_data="create")]
    ]

    await update.message.reply_text(
        "Welcome to the LFH Medical Launch invitation service.\n\n"
        "Tap the button below, then enter the guest's name exactly as you want it "
        "to appear on the invitation (for example: Dr John Doe).",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "create":
        context.user_data["awaiting_name"] = True
        await q.message.reply_text(
            "Please enter the guest name.\n\nExample: Dr John Doe"
        )


async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_name"):
        await update.message.reply_text(
            "Tap “Create Personal Invitation” to begin."
        )
        return

    guest = update.message.text.strip()

    if len(guest) < 2 or len(guest) > 80:
        await update.message.reply_text(
            "Please enter a valid guest name (2–80 characters)."
        )
        return

    context.user_data["awaiting_name"] = False

    try:
        image = make_invitation(guest)
    except FileNotFoundError:
        logging.exception("The final invitation template was not found.")
        await update.message.reply_text(
            "The invitation template is missing. Please contact the administrator."
        )
        return

    await update.message.reply_photo(
        photo=image,
        caption=(
            f"💌 Personal invitation for {guest}\n\n"
            "LFH Medical Launch & Community Health Camp\n"
            "We are pleased to invite you to the Launch and Grand Opening of LFH Medical.\n"
            "Then there will be a health camp under the theme: \"Healthy Community, Healthy Nation.\"\n"
            "Your presence will be of great honour!\n\n"
            "Saturday, 3rd October 2026 • 9:00 AM – 5:00 PM"
        ),
    )


def main():
    if not PUBLIC_URL:
        raise RuntimeError(
            "RENDER_EXTERNAL_URL is missing. Deploy this version as a Render Web Service."
        )

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
    
