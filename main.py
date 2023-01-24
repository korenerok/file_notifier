from datetime import time
import pytz
from telegram.ext import Application, CommandHandler,JobQueue
from configparser import ConfigParser
import logging
import utils

config = ConfigParser()
configfile = 'bot.conf'

config.read(f"./{configfile}")
token = config['SETTINGS_BOT']['token']
scanPath = config['SETTINGS']['path']
inboxPath = config['SETTINGS']['inboxPath']

def truncated_msg(text):
    if len(text) >= 4000:
        result = f"{text[:4000]}...\n \n"
        result += f"MESSAGE TRUNCATED DUE TO TELEGRAM MAX MESSAGE LENGTH"
        return result
    else:
        return text



async def start(update,context):
    """Gives a hearty salutation"""
    user = update.effective_user
    await update.message.reply_text(f"Greetings {user.username} !")

async def help(update,context):
    """List all available commands"""
    msg = """/ross - show the new files in Ross's folder.
/anderson - show the new files in Anderson's folder.
/cano - show the new files in Cano's folder.
/garonzik - show the new files in Garonzik's folder.
/help - List all available commands. 
            """
    await update.message.reply_text(msg)

async def chatId(update,context):
    """Returns the chat id where the bot responds to"""
    chatId = update.message.chat.id
    await update.message.reply_text(chatId)

async def scheduled_tasks(context):
    duplicate =  utils.duplicate()
    if duplicate != None:
        await context.bot.send_message(
            chat_id = config['SETTINGS']['response_id'],
            text = truncated_msg(duplicate)
        )        
    utils.record_new_files()
    utils.categorize_archives()    
    printer = utils.print_files()
    if printer != None:
        await context.bot.send_message(
            chat_id = config['SETTINGS']['response_id'],
            text = truncated_msg(printer)
        )        
    
    
async def count_new_files_roos(update,context):
    msg = utils.count_new_files("ROSS")
    msg = truncated_msg(msg)
    await update.message.reply_text(msg)
    
async def count_new_files_anderson(update,context):
    msg = utils.count_new_files("ANDERSON")
    msg = truncated_msg(msg)
    await update.message.reply_text(msg)
    
async def count_new_files_cano(update,context):
    msg = utils.count_new_files("CANO")
    msg = truncated_msg(msg)
    await update.message.reply_text(msg)
    
async def count_new_files_garonzik(update,context):
    msg = utils.count_new_files("GARONZIK")
    msg = truncated_msg(msg)
    await update.message.reply_text(msg)
    
    
    


def main():
    """Start the bot"""
    application = Application.builder().token(token).build()
    logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    application.add_handler(CommandHandler('chat_id', chatId))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help))
    application.add_handler(CommandHandler('helpme', help))
    application.add_handler(CommandHandler('ross', count_new_files_roos))
    application.add_handler(CommandHandler('anderson', count_new_files_anderson))
    application.add_handler(CommandHandler('cano', count_new_files_cano))
    application.add_handler(CommandHandler('garonzik', count_new_files_garonzik))
    application.job_queue.run_repeating(scheduled_tasks, interval=100, first = time(hour=6, minute=0, second=0, tzinfo=pytz.timezone('US/Eastern')), last= time(hour=19, minute=0, second=0, tzinfo=pytz.timezone('US/Eastern')))
    print('Bot started')
    application.run_polling()

if __name__ == "__main__":
    main()
