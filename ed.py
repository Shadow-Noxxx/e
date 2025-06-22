import logging
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.helpers import escape_markdown

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dictionary: chat_id -> set of user_ids
authorized_users_per_chat = {}

# Inline buttons for /start
def get_main_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Support", url="https://t.me/+LWp85IaDkzsyZjZl")],
        [InlineKeyboardButton("🤖 Bot Channel", url="https://t.me/FOS_BOTS")]
    ])

# Utility to get target user

# Inline buttons for /start
def get_main_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Support", url="https://t.me/YourSupportGroup")],
        [InlineKeyboardButton("📄 Docs", url="https://example.com/docs")],
        [InlineKeyboardButton("🤖 Bot Channel", url="https://t.me/YourBotChannel")]
    ])

# Utility to get target user
def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            return int(context.args[0])
        except ValueError:
            return None
    return None

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """👋 *Welcome to EditGuard Bot\!*

🔒 This bot deletes edited messages from unauthorized users\.
Admins can manage permissions using:
/auth, /unauth, /authlist

💡 *Tip:* Reply to a user’s message and use /auth or /unauth""",
        parse_mode="MarkdownV2",
        reply_markup=get_main_buttons()
    )

# /auth
async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    member = await update.effective_chat.get_member(user_id)

    if member.status in ['administrator', 'creator']:
        target_id = get_target_user(update, context)
        if target_id is None:
            await update.message.reply_text("⚠️ Reply to a user or use `/auth <user_id>`", parse_mode="MarkdownV2")
            return

        authorized_users_per_chat.setdefault(chat_id, set()).add(target_id)
        await update.message.reply_text(
            f"✅ User `{target_id}` is now authorized in this group.",
            parse_mode="MarkdownV2"
        )
    else:
        await update.message.reply_text("⛔ You're not allowed to use this command.", parse_mode="MarkdownV2")

# /unauth
async def unauth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    member = await update.effective_chat.get_member(user_id)

    if member.status in ['administrator', 'creator']:
        target_id = get_target_user(update, context)
        if target_id is None:
            await update.message.reply_text("⚠️ Reply to a user or use `/unauth <user_id>`", parse_mode="MarkdownV2")
            return

        authorized_users_per_chat.setdefault(chat_id, set()).discard(target_id)
        await update.message.reply_text(
            f"❌ User `{target_id}` has been unauthorised in this group.",
            parse_mode="MarkdownV2"
        )
    else:
        await update.message.reply_text("⛔ You're not allowed to use this command.", parse_mode="MarkdownV2")

# /authlist
async def authlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_ids = authorized_users_per_chat.get(chat_id, set())

    if not user_ids:
        await update.message.reply_text(
            "📋 *No users are currently authorized in this group\.*",
            parse_mode="MarkdownV2"
        )
        return

    lines = ["📄 *Authorized Users:*"]
    for uid in user_ids:
        try:
            member = await update.effective_chat.get_member(uid)
            safe_name = escape_markdown(member.user.full_name, version=2)
            lines.append(f"👤 [{safe_name}](tg://user?id={uid})")
        except:
            lines.append(f"❔ Unknown User (`{uid}`)")

    await update.message.reply_text("\n".join(lines), parse_mode="MarkdownV2")

# Edited message handler
async def on_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    edited = update.edited_message
    if not edited or not edited.from_user:
        return

    chat_id = edited.chat_id
    user_id = edited.from_user.id
    allowed_users = authorized_users_per_chat.get(chat_id, set())

    if user_id in allowed_users:
        return

    try:
        await edited.delete()
        safe_name = escape_markdown(edited.from_user.full_name, version=2)

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"""🚨 *Message Edit Detected\!*

👤 [_{safe_name}_](tg://user?id={user_id}) tried to *edit* their message\.
🗑️ So I deleted it\.

🔐 Only *authorized users* can edit messages here\.
Use `/auth {user_id}` if it was a mistake\.""",
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.warning(f"Failed to delete edited message from {user_id}: {e}")

# Main
def main():
    TOKEN = "7272212814:AAE7WLE7S6pflh8xMtRgX3bms0a_vPo2XjY"  # Replace with your bot token
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auth", auth))
    app.add_handler(CommandHandler("unauth", unauth))
    app.add_handler(CommandHandler("authlist", authlist))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, on_edited_message))

    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
