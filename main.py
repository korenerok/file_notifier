from telegram.ext import Application, CommandHandler
from configparser import ConfigParser
import logging
import utils

config = ConfigParser()
configfile = 'bot.conf'

config.read(f"./{configfile}")
token = config['SETTINGS_BOT']['token']

async def start(update,context):
    """Gives a hearty salutation"""
    user = update.effective_user
    await update.message.reply_text(f"Greetings {user.username} !")

async def help(update,context):
    """List all available commands"""
    msg = """/help = List all available commands.
/start = Gives a hearty salutation.
/chat_id = Returns the chat id where the bot responds to. 
            """
    await update.message.reply_text(msg)

async def chatId(update,context):
    """Returns the chat id where the bot responds to"""
    chatId = update.message.chat.id
    await update.message.reply_text(chatId)

def record_new_files(update,context):
    text = utils.record_new_files()


def main():
    """Start the bot"""
    application = Application.builder().token(token).build()
    logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    application.add_handler(CommandHandler('chat_id', chatId))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help))
    application.add_handler(CommandHandler('helpme', help))
    print('Bot started')
    application.run_polling()

if __name__ == "__main__":
    main()
