#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
import requests
import json
import subprocess
import base64
from datetime import timedelta, datetime, timezone
from telegram.ext import Updater, CommandHandler
from dateutil.parser import parse
from random import randrange
import feedparser
from peewee import Model, SqliteDatabase, IntegerField
import os


HEROKUAPP = os.getenv("HEROKUAPP", "uilianries")
TOKEN = os.getenv("TELEGRAM_TOKEN", None)
DATABASE = SqliteDatabase('pb.sqlite')


class BaseModel(Model):
    class Meta:
        database = DATABASE


class ChatId(BaseModel):
    chatid = IntegerField(unique=True)


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def start(update, context):
    context.bot.send_message(chat_id=update.message.chat_id, text='Olá! Procurando pelo pior podcast das podosfera?\nAcesse http://procurandobitucas.com/')


def episodios(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Todos os episódios: http://procurandobitucas.com/podcast/episodios/")


def twitter(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Twitter oficial do PB: https://twitter.com/procurabitucas")


def instagram(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Instagram oficial do PB: https://www.instagram.com/procurandobitucas")


def spotify(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Ouvir o PB no Spotify: https://open.spotify.com/show/79cz6YQpsKETIZOeHADXeD?si=Pi1YuzU0Tx-d-AfADSYpvg")


def apple(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Ouvir o PR no Apple Podcast: https://itunes.apple.com/br/podcast/procurando-bitucas-um-podcast/id1336239884?mt=2&ls=1")


def deezer(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Ouvir o PR no Deezer: https://www.deezer.com/br/show/520392")


def dono(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Quem é o dono do PB: https://twitter.com/washi_sena")


def guerreirinho(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Quem é o host do PB: https://twitter.com/alcofay2k")

def fotografo(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Quem é o fotógrafo do PB: https://twitter.com/mmessiasjunior")


def telegram(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Grupo oficial do PB no Telegram: https://t.co/vY2s8UZwLQ?amp=1")


def whatsapp(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Não tem grupo de Zap Zap, use o /telegram")


def xvideos(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Canal no XVideos foi derrubado por excesso de acessos, mas você pode assistir pelo óculos 4D.")


def ultimo(update, context):
    rss_feed = feedparser.parse("http://procurandobitucas.com/podcast/feed/podcast/")
    last_ep = rss_feed["entries"][0]
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Último episódio disponível: {} - {}".format(last_ep["title"], last_ep["link"]))


def error(update, context):
    logger.warning('Ops! "%s" deu erro "%s"', update, context.error)


def help(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Use / pra listar os comandos ou utilize o seu óculos 4D!")


def inscritos(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Computei uma legião aproximada em {} fãs!".format(randrange(3000000000, 4000000000)))


def notificar(update, context):
    if is_subscribed(update.message.chat_id):
        logging.info("User subscribed again: {}".format(update.message.from_user.username))
        context.bot.send_message(chat_id=update.message.chat_id, text="Você já está inscrito para receber novos episódios.")
        return

    logging.info("User subscribed: {}".format(update.message.from_user.username))
    context.bot.send_message(chat_id=update.message.chat_id, text="Você será notificado quando sair um novo episódio!")
    add_chat_id(update.message.chat_id)


def notify_assignees(context):
    rss_feed = feedparser.parse("http://procurandobitucas.com/podcast/feed/podcast/")
    last_ep = rss_feed["entries"][0]
    date = last_ep["published"]
    logger.info("Last ep date: {}".format(date))

    parsed_date = parse(date)
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    if now - parsed_date < timedelta(minutes=15):
        for entry in ChatId.select():
            logger.info("New episode: {} - Send to {}".format(date, entry.chatid))
            context.bot.send_message(chat_id=entry.chatid, text="Novo episódio - {}: {}".format(last_ep["title"], last_ep["link"]))


def parar(update, context):
    if is_subscribed(update.message.chat_id):
        logging.info("User unsubscribed: {}".format(update.message.from_user.username))
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text='Você não receberá novas notificações de episódios.')
        remove_chat_id(update.message.chat_id)
    else:
        logging.info("User unsubscribed again: {}".format(update.message.from_user.username))
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text='Você já não está inscrito para receber notficações.')


def update_db():
    with open("pb.sqlite", "rb") as db_fd:
        content = db_fd.read()
        encoded = base64.b64encode(content)
    payload = {"branch":"main", "author_email":"uilianries@gmail.com", "author_name":"uilianries", "file_path":"pb.slqite.base64", "content": encoded.decode('ascii'), "commit_message":"update db"}
    headers = {"PRIVATE-TOKEN": os.getenv("GITLAB_TOKEN", "FALSE"), "Content-Type": "application/json"}
    response = requests.put("https://gitlab.com/api/v4/projects/30298296/repository/files/pb.sqlite.base64", data=json.dumps(payload), headers=headers)
    if not response.ok:
        logger.error("Could not commit: {}".format(response.json()))


def create_db():
    if not os.path.exists("pb.sqlite"):
        DATABASE.connect()
        DATABASE.create_tables([ChatId])
    with open("pb.sqlite", "rb") as db_fd:
        content = db_fd.read()
        encoded = base64.b64encode(content)
    payload = {"branch":"main", "author_email":"uilianries@gmail.com", "author_name":"uilianries",  "file_path":"pb.slqite.base64", "content": encoded.decode('ascii'), "commit_message":"update db"}
    headers = {"PRIVATE-TOKEN": os.getenv("GITLAB_TOKEN", "FALSE"), "Content-Type": "application/json"}
    response = requests.post("https://gitlab.com/api/v4/projects/30298296/repository/files/pb.sqlite.base64", data=json.dumps(payload), headers=headers)
    if not response.ok:
        logger.error("Could not commit: {}".format(response.json()))


def download_db():
    headers = {"PRIVATE-TOKEN": os.getenv("GITLAB_TOKEN", "FALSE")}
    response = requests.get("https://gitlab.com/api/v4/projects/30298296/repository/files/pb%2Esqlite%2Ebase64/raw?ref=main", headers=headers)
    if not response.ok:
        logger.error("Could not download file: {}".format(response.json()))
        if "404 File Not Found" in response.json()["message"]:
            create_db()
        return
    decoded = base64.b64decode(response.content.decode('ascii'))
    with open("pb.sqlite", "wb") as file_db:
        file_db.write(decoded)


def add_chat_id(chat_id):
    ChatId.insert(chatid=chat_id).on_conflict_ignore().execute()
    update_db()


def remove_chat_id(chat_id):
    query = ChatId.delete().where(ChatId.chatid == chat_id)
    query.execute()
    update_db()


def is_subscribed(chat_id):
    return ChatId.select().where(ChatId.chatid == chat_id)


def main():
    if TOKEN is None:
        logger.error("TELEGRAM TOKEN is Empty.")
        raise ValueError("TELEGRAM_TOKEN is unset.")

    download_db()

    DATABASE.connect(reuse_if_open=True)

    updater = Updater(TOKEN, use_context=True)

    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(CommandHandler("ajuda", help))
    updater.dispatcher.add_handler(CommandHandler("episodios", episodios))
    updater.dispatcher.add_handler(CommandHandler("twitter", twitter))
    updater.dispatcher.add_handler(CommandHandler("instagram", instagram))
    updater.dispatcher.add_handler(CommandHandler("spotify", spotify))
    updater.dispatcher.add_handler(CommandHandler("apple", apple))
    updater.dispatcher.add_handler(CommandHandler("deezer", deezer))
    updater.dispatcher.add_handler(CommandHandler("telegram", telegram))
    updater.dispatcher.add_handler(CommandHandler("dono", dono))
    updater.dispatcher.add_handler(CommandHandler("guerreirinho", guerreirinho))
    updater.dispatcher.add_handler(CommandHandler("fotografo", fotografo))
    updater.dispatcher.add_handler(CommandHandler("whatsapp", whatsapp))
    updater.dispatcher.add_handler(CommandHandler("xvideos", xvideos))
    updater.dispatcher.add_handler(CommandHandler('notificar', notificar))
    updater.dispatcher.add_handler(CommandHandler('parar', parar))
    updater.dispatcher.add_handler(CommandHandler('ultimo', ultimo))
    updater.dispatcher.add_handler(CommandHandler('inscritos', inscritos))
    updater.dispatcher.add_error_handler(error)
    updater.job_queue.run_repeating(notify_assignees, 900, context=updater.bot)

    updater.start_polling()
    updater.idle()
    DATABASE.close()


if __name__ == '__main__':
    main()
