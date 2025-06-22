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
from telegram.constants import ChatMemberStatus

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Dictionary: chat_id -> set of user_ids
authorized_users_per_chat = {}

# Constants for admin status checks
ALLOWED_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}

# Inline buttons for /start
def get_main_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Support", url="https://t.me/FOS_BOTS")],
        [InlineKeyboardButton("🤖 Bot Channel", url="https://t.me/fos_bots")]
    ])

# Utility to get target user
async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            return int(context.args[0])
        except (ValueError, IndexError):
            return None
    return None

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    
    await update.message.reply_text(
        """👋 *Welcome to EditGuard Bot\!*

🔒 This bot deletes edited messages from unauthorized users\.
Admins can manage permissions using:
/auth, /unauth, /authlist

💡 *Tip:* Reply to a user's message and use /auth or /unauth""",
        parse_mode="MarkdownV2",
        reply_markup=get_main_buttons()
    )

# /auth command handler
async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    try:
        member = await update.effective_chat.get_member(user_id)
        if member.status not in ALLOWED_STATUSES:
            await update.message.reply_text("⛔ You're not allowed to use this command.", parse_mode="MarkdownV2")
            return

        target_id = await get_target_user(update, context)
        if target_id is None:
            await update.message.reply_text("⚠️ Reply to a user or use `/auth <user_id>`", parse_mode="MarkdownV2")
            return

        authorized_users_per_chat.setdefault(chat_id, set()).add(target_id)
        await update.message.reply_text(
            f"✅ User `{target_id}` is now authorized in this group.",
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"Error in /auth command: {e}")
        await update.message.reply_text("⚠️ An error occurred while processing your request.")

# /unauth command handler
async def unauth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    try:
        member = await update.effective_chat.get_member(user_id)
        if member.status not in ALLOWED_STATUSES:
            await update.message.reply_text("⛔ You're not allowed to use this command.", parse_mode="MarkdownV2")
            return

        target_id = await get_target_user(update, context)
        if target_id is None:
            await update.message.reply_text("⚠️ Reply to a user or use `/unauth <user_id>`", parse_mode="MarkdownV2")
            return

        authorized_users_per_chat.setdefault(chat_id, set()).discard(target_id)
        await update.message.reply_text(
            f"❌ User `{target_id}` has been unauthorised in this group.",
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"Error in /unauth command: {e}")
        await update.message.reply_text("⚠️ An error occurred while processing your request.")

# /authlist command handler
async def authlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return
    
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
        except Exception as e:
            logger.warning(f"Couldn't get user info for {uid}: {e}")
            lines.append(f"❔ Unknown User (`{uid}`)")

    await update.message.reply_text("\n".join(lines), parse_mode="MarkdownV2")

# Edited message handler
async def on_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.edited_message or not update.edited_message.from_user:
        return
    
    edited = update.edited_message
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
        logger.error(f"Failed to handle edited message from {user_id}: {e}")

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling update {update}: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("⚠️ An unexpected error occurred. Please try again.")

# Main function
def main():
    TOKEN = "7272212814:AAE7WLE7S6pflh8xMtRgX3bms0a_vPo2XjY"  # Replace with your bot token
    
    try:
        app = ApplicationBuilder().token(TOKEN).build()

        # Register handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("auth", auth))
        app.add_handler(CommandHandler("unauth", unauth))
        app.add_handler(CommandHandler("authlist", authlist))
        app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, on_edited_message))
        
        # Register error handler
        app.add_error_handler(error_handler)

        logger.info("Bot is starting...")
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}")

if __name__ == "__main__":
    main()
