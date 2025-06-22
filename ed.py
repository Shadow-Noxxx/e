import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory authorized users
authorized_users = set()

# Inline keyboard buttons
def get_main_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Support", url="https://t.me/+LWp85IaDkzsyZjZl")],
        [InlineKeyboardButton("🤖 Bot Channel", url="https://t.me/fos_bots")]
    ])

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *Welcome to EditGuard Bot\\!*\n\n"
        "🔒 This bot automatically *deletes edited messages* from unauthorized users\\.\n\n"
        "⚙️ Admins can control permissions using:\n"
        "`/auth` — Authorize user\n"
        "`/unauth` — Revoke editing rights\n\n"
        "💡 *Tip:* Reply to a user’s message and send `/auth` or `/unauth`\n"
    )
    await update.message.reply_text(
        text,
        parse_mode="MarkdownV2",
        reply_markup=get_main_buttons()
    )

# Get user from reply or args
def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            return int(context.args[0])
        except ValueError:
            return None
    return None

# /auth
async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    requester_id = update.effective_user.id
    member = await update.effective_chat.get_member(requester_id)

    if requester_id in authorized_users or member.status in ['administrator', 'creator']:
        target_id = get_target_user(update, context)
        if target_id is None:
            await update.message.reply_text("⚠️ *Usage:* Reply to a user or use `/auth <user_id>`", parse_mode="MarkdownV2")
            return

        authorized_users.add(target_id)
        await update.message.reply_text(
            f"✅ User `{target_id}` is *now authorized* to edit messages\\.",
            parse_mode="MarkdownV2"
        )
    else:
        await update.message.reply_text("⛔ *Permission Denied:* Only admins can authorize users\\.", parse_mode="MarkdownV2")

# /unauth
async def unauth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    requester_id = update.effective_user.id
    member = await update.effective_chat.get_member(requester_id)

    if requester_id in authorized_users or member.status in ['administrator', 'creator']:
        target_id = get_target_user(update, context)
        if target_id is None:
            await update.message.reply_text("⚠️ *Usage:* Reply to a user or use `/unauth <user_id>`", parse_mode="MarkdownV2")
            return

        authorized_users.discard(target_id)
        await update.message.reply_text(
            f"🚫 User `{target_id}` has been *removed* from the authorized list\\.",
            parse_mode="MarkdownV2"
        )
    else:
        await update.message.reply_text("⛔ *Permission Denied:* Only admins can unauthorize users\\.", parse_mode="MarkdownV2")

# Edited messages
from telegram.helpers import escape_markdown

async def on_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    edited = update.edited_message
    if not edited or not edited.from_user:
        return  # Ignore system or unknown edits

    user = edited.from_user
    user_id = user.id

    if user_id in authorized_users:
        return  # Authorized user – skip deletion

    try:
        await edited.delete()
        logger.info(f"🧹 Deleted edited message from unauthorized user {user_id}.")

        # Escape user name safely
        safe_name = escape_markdown(user.full_name, version=2)

        # Send a fancy warning message
        await context.bot.send_message(
            chat_id=edited.chat_id,
            text=(
                f"🚨 *Message Edit Detected\\!* \n\n"
                f"👤 [_{safe_name}_](tg://user?id={user_id}) tried to *edit* their message\\. "
                f"\n\n🗑️ But I'm strict\\. *So I deleted it\\!*"
                f"\n\n🔐 Only *authorized users* are allowed to edit messages here\\.\n"
                f"Ask an admin to use `/auth {user_id}` if it was a mistake\\."
            ),
            parse_mode="MarkdownV2"
        )

    except Exception as e:
        logger.error(f"❌ Failed to delete edited message from {user_id}: {e}")
        await context.bot.send_message(
            chat_id=edited.chat_id,
            text="⚠️ *Error:* Unable to delete the edited message\\. Please report this to an admin\\.",
            parse_mode="MarkdownV2"
        )


from telegram.helpers import escape_markdown

async def authlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized_users:
        await update.message.reply_text(
            "📛 *No users are currently authorized to edit messages\\.*",
            parse_mode="MarkdownV2"
        )
        return

    lines = ["📋 *Authorized Users List:*"]
    for user_id in authorized_users:
        try:
            member = await update.effective_chat.get_member(user_id)
            name = member.user.full_name
            safe_name = escape_markdown(name, version=2)
            lines.append(f"👤 [{safe_name}](tg://user?id={user_id})")
        except Exception:
            # In case the user left the group or is not found
            lines.append(f"❔ Unknown User (`{user_id}`)")

    text = "\n".join(lines)
    await update.message.reply_text(text, parse_mode="MarkdownV2")

# -*- coding: utf-8 -*-



# Main
def main():
    TOKEN = "7272212814:AAE7WLE7S6pflh8xMtRgX3bms0a_vPo2XjY"  # Replace with your actual bot token
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auth", auth))
    app.add_handler(CommandHandler("unauth", unauth))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, on_edited_message))
    app.add_handler(CommandHandler("authlist", authlist))
    logger.info("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
