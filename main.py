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
settings = config['SETTINGS']
providers= config['SETTINGS']['providers'].split(',')

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

# async def duplicated_tasks(context):
    #utils.convert_pdf() 
    

async def scheduled_tasks(context):
           
    utils.record_new_files()
    utils.categorize_archives()    
    printer = utils.print_files()
    if printer is not None:
        await context.bot.send_message(
            chat_id = config['SETTINGS']['response_id'],
            text = truncated_msg(printer)
        )    

async def scheduled_msj(context):
    for section in config.sections():
        provider= section.format(['']).upper()
        if provider in providers:
            chat_id = config[provider]['chat_id']
            msg = utils.count_new_files(provider)
            if msg != f"•{provider}: no new documents\n":                
                await context.bot.send_message(
                chat_id = chat_id,
                text = truncated_msg(msg)
                )

async def scheduled_msj_once(context):
    for section in config.sections():
        provider= section.format(['']).upper()
        if provider in providers:
            chat_id = config[provider]['chat_id']
            msg = utils.count_new_files(provider)                    
            await context.bot.send_message(
            chat_id = chat_id,
            text = truncated_msg(msg)
            )
       
async def count_new_files_ross(update,context):
    msg = utils.count_new_files("ROSS")
    msg = truncated_msg(msg)
    await update.message.reply_html(msg)
    
async def count_new_files_anderson(update,context):
    msg = utils.count_new_files("ANDERSON")
    msg = truncated_msg(msg)
    await update.message.reply_html(msg)
    
async def count_new_files_cano(update,context):
    msg = utils.count_new_files("CANO")
    msg = truncated_msg(msg)
    await update.message.reply_html(msg)
    
async def count_new_files_garonzik(update,context):
    msg = utils.count_new_files("GARONZIK")
    msg = truncated_msg(msg)
    await update.message.reply_html(msg)

async def count_all_new_files(update,context):
    msg = utils.count_all_new_files()
    msg = truncated_msg(msg)
    await update.message.reply_html(msg)

async def count_all_new_files_without_update_new_flag(update,context):
    msg = utils.count_all_new_files(False)
    msg = truncated_msg(msg)
    await update.message.reply_html(msg)

def main():
    """Start the bot"""
    application = Application.builder().token(token).build()
    logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    application.add_handler(CommandHandler('chat_id', chatId))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help))
    application.add_handler(CommandHandler('helpme', help))
    application.add_handler(CommandHandler('all', count_all_new_files))
    application.add_handler(CommandHandler('all_for_test', count_all_new_files_without_update_new_flag))
    application.add_handler(CommandHandler('ross', count_new_files_ross))
    application.add_handler(CommandHandler('anderson', count_new_files_anderson))
    application.add_handler(CommandHandler('cano', count_new_files_cano))
    application.add_handler(CommandHandler('garonzik', count_new_files_garonzik))
    #application.job_queue.run_repeating(duplicated_tasks, interval=45, first = time(hour=6, minute=0, second=0, tzinfo=pytz.timezone('US/Eastern')), last= time(hour=19, minute=0, second=0, tzinfo=pytz.timezone('US/Eastern')))
    application.job_queue.run_repeating(scheduled_tasks, interval=120, first = time(hour=6, minute=0, second=0, tzinfo=pytz.timezone('US/Eastern')), last= time(hour=19, minute=0, second=0, tzinfo=pytz.timezone('US/Eastern')))
    application.job_queue.run_repeating(scheduled_msj, interval=7200, first = time(hour=6, minute=0, second=0, tzinfo=pytz.timezone('US/Eastern')), last= time(hour=17, minute=0, second=0, tzinfo=pytz.timezone('US/Eastern')))
    application.job_queue.run_daily(scheduled_msj_once, time(hour=7, minute=5, second=00, tzinfo=pytz.timezone('US/Eastern')), days=tuple(range(1,6)))
    application.job_queue.run_daily(scheduled_msj_once, time(hour=12, minute=00, second=00, tzinfo=pytz.timezone('US/Eastern')), days=tuple(range(1,6)))
    print('Bot started')
    application.run_polling()

if __name__ == "__main__":
    main()
