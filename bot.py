#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import os


PORT = int(os.environ.get('PORT', 5000))
HEROKUAPP = os.getenv("HEROKUAPP", "uilianries")
TOKEN = os.getenv("TELEGRAM_TOKEN", None)


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')

def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')

def episodios(update, context):
    update.message.reply_text("Todos os episódios: http://procurandobitucas.com/podcast/episodios/")

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    if TOKEN is None:
        logger.error("TELEGRAM TOKEN is Empty.")
        raise ValueError("TELEGRAM_TOKEN is unset.")

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("episodios", episodios))

    dp.add_error_handler(error)

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()