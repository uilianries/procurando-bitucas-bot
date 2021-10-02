#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from datetime import timedelta, datetime
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import dateutil
import feedparser
import os


PORT = int(os.environ.get('PORT', 5000))
HEROKUAPP = os.getenv("HEROKUAPP", "uilianries")
TOKEN = os.getenv("TELEGRAM_TOKEN", None)
LASTEST_EP = None


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def start(update, context):
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
    logger.warning('Ops! "%s" deu erro "%s"', update, context.error)


def help(update, context):
    update.message.reply_text("Sem ajuda! Melhor chamar o Batman!")


def rss_monitor(bot, update, job_queue):
    bot.send_message(chat_id=update.message.chat_id, text="Irei notificar quando sair um episódio novo!")
    interval = 4 * 3600
    job_queue.run_repeating(notify_assignees, interval, context=update.message.chat_id)


def notify_assignees(bot, job):
    rss_feed = feedparser.parse("http://procurandobitucas.com/podcast/feed/podcast/")
    last_ep = rss_feed["entries"][0]
    date = last_ep["published"]
    parsed_date = dateutil.parser.parse(date)
    now = datetime.utcnow()
    if now - parsed_date < timedelta(hours=4):
        bot.send_message(chat_id=job.context, text="Novo episódio - {}: {}".format(last_ep["title"], last_ep["link"]))


def stop_notify(bot, update, job_queue):
    bot.send_message(chat_id=update.message.chat_id, text='Notificação de novos episódios foi encerardo.')
    job_queue.stop()


def main():
    if TOKEN is None:
        logger.error("TELEGRAM TOKEN is Empty.")
        raise ValueError("TELEGRAM_TOKEN is unset.")

    updater = Updater(TOKEN, use_context=True)

    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(CommandHandler("help", help))
    updater.dispatcher.add_handler(CommandHandler("episodios", episodios))
    updater.dispatcher.add_handler(CommandHandler("twitter", twitter))
    updater.dispatcher.add_handler(CommandHandler("instagram", instagram))
    updater.dispatcher.add_handler(CommandHandler("spotify", spotify))
    updater.dispatcher.add_handler(CommandHandler("apple", apple))
    updater.dispatcher.add_handler(CommandHandler("deezer", deezer))
    updater.dispatcher.add_handler(CommandHandler("telegram", telegram))
    updater.dispatcher.add_handler(CommandHandler("dono", dono))
    updater.dispatcher.add_handler(CommandHandler("guerreirinho", guerreirinho))
    updater.dispatcher.add_handler(CommandHandler("whatsapp", whatsapp))
    updater.dispatcher.add_handler(CommandHandler("xvideos", xvideos))
    updater.dispatcher.add_handler(CommandHandler('notificar', rss_monitor, pass_job_queue=True))
    updater.dispatcher.add_handler(CommandHandler('parar', stop_notify, pass_job_queue=True))

    updater.dispatcher.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
