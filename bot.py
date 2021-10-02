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
    update.message.reply_text('Olá! Procurando pelo pior podcast das podosfera?\nAcesse http://procurandobitucas.com/')

def episodios(update, context):
    update.message.reply_text("Todos os episódios: http://procurandobitucas.com/podcast/episodios/")

def twitter(update, context):
    update.message.reply_text("Twitter oficial do PB: https://twitter.com/procurabitucas")

def instagram(update, context):
    update.message.reply_text("Instagram oficial do PB: https://www.instagram.com/procurandobitucas")

def spotify(update, context):
    update.message.reply_text("Ouvir o PB no Spotify: https://open.spotify.com/show/79cz6YQpsKETIZOeHADXeD?si=Pi1YuzU0Tx-d-AfADSYpvg")

def apple(update, context):
    update.message.reply_text("Ouvir o PR no Apple Podcast: https://itunes.apple.com/br/podcast/procurando-bitucas-um-podcast/id1336239884?mt=2&ls=1")

def deezer(update, context):
    update.message.reply_text("Ouvir o PR no Apple Podcast: https://www.deezer.com/br/show/520392")

def dono(update, context):
    update.message.reply_text("Quem é o dono do PB: https://twitter.com/washi_sena")

def guerreirinho(update, context):
    update.message.reply_text("Quem é o host do PB: https://twitter.com/alcofay2k")

def telegram(update, context):
    update.message.reply_text("Grupo oficial do PB no Telegram: https://t.co/vY2s8UZwLQ?amp=1")

def whatsapp(update, context):
    update.message.reply_text("Não tem grupo de Zap Zap, vai usar o Telegram!")

def xvideos(update, context):
    update.message.reply_text("Canal no XVideos foi derrubado por excesso de acessos")

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
    dp.add_handler(CommandHandler("twitter", twitter))
    dp.add_handler(CommandHandler("instagram", instagram))
    dp.add_handler(CommandHandler("spotify", spotify))
    dp.add_handler(CommandHandler("apple", apple))
    dp.add_handler(CommandHandler("deezer", deezer))
    dp.add_handler(CommandHandler("telegram", telegram))
    dp.add_handler(CommandHandler("dono", dono))
    dp.add_handler(CommandHandler("guerreirinho", guerreirinho))
    dp.add_handler(CommandHandler("whatsapp", whatsapp))
    dp.add_handler(CommandHandler("xvideos", xvideos))

    dp.add_error_handler(error)

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()