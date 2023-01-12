from telegram.ext import Updater, CommandHandler
from configparser import ConfigParser
import logging

config = ConfigParser()
configfile = 'bot.conf'

config.read(f"./{configfile}")
token = config['SETTING_BOT']['token']

def start(update):
    update.message.reply_text("Greetings!")

def help(update):
    msg = """/help = List all available commands.
            /start = Gives a hearty salutation.
            /chat_id = Returns the chat id where the bot responds to. 
            """
    update.message.reply_text(msg)

def chatId(update):
    chatId = update.message.chat.id
    update.message.reply_text(chatId)

if __name__ == '__main__':
    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher
    logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    dispatcher.add_handler(CommandHandler('chat_id', chatId))
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help))
    dispatcher.add_handler(CommandHandler('helpme', help))
    updater.start_polling()
    print('Bot started')
    updater.idle()