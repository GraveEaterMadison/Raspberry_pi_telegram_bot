from config import AUTHORIZED_USERS

def is_authorized(user_id):
    """Check if the user is in the list of authorized users."""
    return user_id in AUTHORIZED_USERS

async def check_authorization(update, context, command_handler):
    """Check if the user is authorized before calling the command handler."""
    user_id = update.effective_user.id
    if is_authorized(user_id):
        await command_handler(update, context)
    else:
        await update.message.reply_text("You are not authorized to use this bot.")
