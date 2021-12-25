#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
import re
import os
import json
import base64
import random
import configparser

import requests
from typing import Tuple, Optional

from datetime import timedelta, datetime, timezone
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ChatMemberHandler, CallbackContext
from telegram import Update, Chat, ChatMember, ParseMode, ChatMemberUpdated
from dateutil.parser import parse
from random import randrange
import feedparser
import click
from peewee import Model, SqliteDatabase, IntegerField
from google.assistant.embedded.v1alpha2 import embedded_assistant_pb2
from google.assistant.embedded.v1alpha2 import embedded_assistant_pb2_grpc
import google.auth.transport.grpc
import google.auth.transport.requests
import google.oauth2.credentials



CONFIG_FILE = "/etc/bitucas.conf"
ASSISTANT_API_ENDPOINT = 'embeddedassistant.googleapis.com'
DEFAULT_GRPC_DEADLINE = 60 * 3 + 5
HEROKUAPP = os.getenv("HEROKUAPP", "uilianries")
TELEGRAM_TOKEN = None
GITLAB_TOKEN = None
DATABASE = SqliteDatabase('pb.sqlite')
DEVICE_MODEL_ID = None
PROJECT_ID = None
CREDENTIALS_CONTENT = None
ASSISTANT = None


class BaseModel(Model):
    class Meta:
        database = DATABASE


class ChatId(BaseModel):
    chatid = IntegerField(unique=True)


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


ERROR_QUOTES = [
    "Ops! Algo saiu errado! Contate algum humano do PB pra resolver essa merda.",
    "Esse comando não funcionou, eu não assumo esse B.O.! Foi culpa do programador.",
    "Não funcionou e não sou pago pra fazer isso, resolva você o caso.",
    "Não consegui completar o comando, a SkyNet está de folga hoje.",
    "O Guerreirinho tropeçou no cabo de rede, não consegui fazer o que você pediu.",
    "O comando falhou, vai ver o Washi fez teste em produção outra vez.",
    "Não estou com vontade de atender humano folgado hoje, peça pro host.",
    "Você de novo aqui? Vai ver por isso que não está funcionando essa merda.",
    "Esse comando está com interferência causada pelo seu óculos 4D, tire sua cueca e tente novamente",
    "Desculpe, não compreendi o que você escreveu, poderia repetir?",
    "Você tem o intelecto de uma mula, se expresse melhor!",
    "Pensei que o meu dia seria tranquilo, sem um otário para me importunar",
    "Estou indisponível no momento, saí pra comprar cigarros",
    "Não sei, pergunta pra Siri ou pra Alexa",
]


GREETINGS_QUOTES = [
    "Bem-vindo ao Procurando Bitucas! Se está procurando ajuda para parar de fumar disque 136.",
    "Bem-vindo ao Procurando Bitucas! Tente ficar por pelo menos 1 minuto antes de sair do grupo, nosso recorde é de 7 segundos.",
    "Bem-vindo ao Procurando Bitucas! Você acabar de adquirir o kit bituqueiro, que acompanha uma regata suada e um óculos 4D.",
    "Bem-vindo ao Procurando Bitucas! Se inscreva no Only Haters também e nos odeie por apenas $15 USD ao mês.",
    "Bem-vindo ao Procurando Bitucas! Em instantes você será recebido pelo dono ou pelo guerreirinho.",
    "Bem-vindo ao Procurando Bitucas! Sou o bot de relações humanas, minha missão é minerar bitcoin no seu celular, então não feche o Telegram.",
    "Bem-vindo ao Procurando Bitucas! Não somos um grupo de controle de tabagismo, mas fazemos mais mal que drogas pesadas.",
]


GOODBYE_QUOTES = [
    "{} nos deixou, pelo menos um soube a hora certa de parar",
    "{} saiu tarde, espero que não volte",
    "{} adeus!",
    "Acabamos de perder o(a) {}. Alguém xingue no Twitter.",
    "{} se desconectou do grupo. Quem será o próximo?",
]


def extract_status_change(chat_member_update: ChatMemberUpdated,) -> Optional[Tuple[bool, bool]]:
    """Takes a ChatMemberUpdated instance and extracts whether the 'old_chat_member' was a member
    of the chat and whether the 'new_chat_member' is a member of the chat. Returns None, if
    the status didn't change.
    """
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = (
        old_status
        in [
            ChatMember.MEMBER,
            ChatMember.CREATOR,
            ChatMember.ADMINISTRATOR,
        ]
        or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    )
    is_member = (
        new_status
        in [
            ChatMember.MEMBER,
            ChatMember.CREATOR,
            ChatMember.ADMINISTRATOR,
        ]
        or (new_status == ChatMember.RESTRICTED and new_is_member is True)
    )

    return was_member, is_member


def greet_chat_members(update: Update, context: CallbackContext) -> None:
    """Greets new users in chats and announces when someone leaves"""
    member_name = update.chat_member.new_chat_member.user.username
    update.effective_chat.send_message(cid, "Olá {}".format(member_name))

    result = extract_status_change(update.chat_member)
    if result is None:
        return

    was_member, is_member = result
    member_name = update.chat_member.new_chat_member.user.username
    cid = update.message.chat.id

    if not was_member and is_member:
        message = random.choice(GREETINGS_QUOTES)
        update.effective_chat.send_message(cid, message)
    elif was_member and not is_member:
        message = random.choice(GOODBYE_QUOTES)
        update.effective_chat.send_message(cid, message.format(member_name))


class TextAssistant(object):
    """Sample Assistant that supports text based conversations.

    Args:
      language_code: language for the conversation.
      device_model_id: identifier of the device model.
      device_id: identifier of the registered device instance.
      channel: authorized gRPC channel for connection to the
        Google Assistant API.
      deadline_sec: gRPC deadline in seconds for Google Assistant API call.
    """

    def __init__(self, language_code, device_model_id, device_id,
                 channel, deadline_sec):
        self.language_code = language_code
        self.device_model_id = device_model_id
        self.device_id = device_id
        self.conversation_state = None
        self.assistant = embedded_assistant_pb2_grpc.EmbeddedAssistantStub(channel,)
        self.deadline = deadline_sec

    def __enter__(self):
        return self

    def __exit__(self, etype, e, traceback):
        if e:
            return False

    def assist(self, text_query):
        """Send a text request to the Assistant and playback the response."""
        def iter_assist_requests():
            dialog_state_in = embedded_assistant_pb2.DialogStateIn(
                language_code=self.language_code,
                conversation_state=b''
            )
            if self.conversation_state:
                dialog_state_in.conversation_state = self.conversation_state
            config = embedded_assistant_pb2.AssistConfig(
                audio_out_config=embedded_assistant_pb2.AudioOutConfig(
                    encoding='LINEAR16',
                    sample_rate_hertz=16000,
                    volume_percentage=0,
                ),
                dialog_state_in=dialog_state_in,
                device_config=embedded_assistant_pb2.DeviceConfig(
                    device_id=self.device_id,
                    device_model_id=self.device_model_id,
                ),
                text_query=text_query,
            )
            req = embedded_assistant_pb2.AssistRequest(config=config)
            yield req

        display_text = None
        for resp in self.assistant.Assist(iter_assist_requests(), self.deadline):
            if resp.dialog_state_out.conversation_state:
                conversation_state = resp.dialog_state_out.conversation_state
                self.conversation_state = conversation_state
            if resp.dialog_state_out.supplemental_display_text:
                display_text = resp.dialog_state_out.supplemental_display_text
        return display_text


def get_telegram_token():
    global TELEGRAM_TOKEN
    if not TELEGRAM_TOKEN:
        TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", None)
        if not TELEGRAM_TOKEN:
            if not os.path.exists(CONFIG_FILE):
                raise ValueError("Could not obtain TELEGRAM_TOKEN")
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            TELEGRAM_TOKEN = config["tokens"]["telegram"]
    return TELEGRAM_TOKEN


def get_gitlab_token():
    global GITLAB_TOKEN
    if not GITLAB_TOKEN:
        GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", None)
        if not GITLAB_TOKEN:
            if not os.path.exists(CONFIG_FILE):
                raise ValueError("Could not obtain GITLAB_TOKEN")
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            GITLAB_TOKEN = config["tokens"]["gitlab"]
    return GITLAB_TOKEN


def get_device_model_id():
    global DEVICE_MODEL_ID
    if not DEVICE_MODEL_ID:
        DEVICE_MODEL_ID = os.getenv("DEVICE_MODEL_ID", None)
        if not DEVICE_MODEL_ID:
            if not os.path.exists(CONFIG_FILE):
                raise ValueError("Could not obtain DEVICE_MODEL_ID")
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            DEVICE_MODEL_ID = config["oauth"]["device_model_id"]
    return DEVICE_MODEL_ID


def get_project_id():
    global PROJECT_ID
    if not PROJECT_ID:
        PROJECT_ID = os.getenv("PROJECT_ID", None)
        if not PROJECT_ID:
            if not os.path.exists(CONFIG_FILE):
                raise ValueError("Could not obtain PROJECT_ID")
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            PROJECT_ID = config["oauth"]["project_id"]
    return PROJECT_ID


def get_oauth_credentials():
    global CREDENTIALS_CONTENT
    if not CREDENTIALS_CONTENT:
        CREDENTIALS_CONTENT = os.getenv("CREDENTIALS_CONTENT", None)
        if not CREDENTIALS_CONTENT:
            if not os.path.exists(CONFIG_FILE):
                raise ValueError("Could not obtain CREDENTIALS_CONTENT")
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            CREDENTIALS_CONTENT = config["oauth"]["credentials"]
    return CREDENTIALS_CONTENT



def assistant(update, context):
    message = update.message
    cid = update.message.chat.id
    if message.chat.type == 'private':
        display_text = ASSISTANT.assist(text_query=message.text)
        context.bot.send_message(cid, display_text)
    # If in a group, only reply to mentions.
    elif "@procurandobitucasbot" in update.message.text.lower():
        # Strip first word (the mention) from message text.
        index = update.message.text.lower().find("@procurandobitucasbot")
        message_text = update.message.text[:index] + update.message.text[index+21:]
        if message_text.strip():
            # Get response from Google Assistant API.
            display_text = ASSISTANT.assist(text_query=message_text)
            # Verify that the message is in an authorized chat or from an
            # authorized user.
            if display_text is not None:
                context.bot.send_message(cid, display_text)
            else:
                context.bot.send_message(cid, get_error_message())
        else:
            context.bot.send_message(cid, "Você me mencionou, mas não disse o que quer.")


def get_error_message():
    return random.choice(ERROR_QUOTES)


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


def ranking(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Acesse https://chartable.com/podcasts/procurando-bitucas para obter a posição atual."
                             "\nNão esqueça de falar mal dos outros podcasts da categoria hobbies")


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
    headers = {"PRIVATE-TOKEN": get_gitlab_token(), "Content-Type": "application/json"}
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
    headers = {"PRIVATE-TOKEN": get_gitlab_token(), "Content-Type": "application/json"}
    response = requests.post("https://gitlab.com/api/v4/projects/30298296/repository/files/pb.sqlite.base64", data=json.dumps(payload), headers=headers)
    if not response.ok:
        logger.error("Could not commit: {}".format(response.json()))


def download_db():
    headers = {"PRIVATE-TOKEN": get_gitlab_token()}
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

@click.command()
@click.option('--api-endpoint', default=ASSISTANT_API_ENDPOINT,
              metavar='<api endpoint>', show_default=True,
              help='Address of Google Assistant API service.')
@click.option('--credentials-path',
              metavar='<credentials path>', show_default=True,
              default=os.path.join(click.get_app_dir('google-oauthlib-tool'),
                                   'credentials.json'),
              help='Path to read OAuth2 credentials.')
@click.option('--lang', show_default=True,
              metavar='<language code>',
              default='pt-BR',
              help='Language code of the Assistant')
@click.option('--verbose', '-v', is_flag=True, default=False,
              help='Verbose logging.')
@click.option('--grpc-deadline', default=DEFAULT_GRPC_DEADLINE,
              metavar='<grpc deadline>', show_default=True,
              help='gRPC deadline in seconds')
def main(api_endpoint, credentials_path, lang, verbose,
         grpc_deadline, *args, **kwargs):
    if get_telegram_token() is None:
        logger.error("TELEGRAM TOKEN is Empty.")
        raise ValueError("TELEGRAM_TOKEN is unset.")

    download_db()

    DATABASE.connect(reuse_if_open=True)
    updater = Updater(get_telegram_token(), use_context=True)
    logging.info("TELEGRAM: {}".format(get_telegram_token()))

    try:
        credentials = google.oauth2.credentials.Credentials(token=None, **json.loads(get_oauth_credentials()))
        http_request = google.auth.transport.requests.Request()
        credentials.refresh(http_request)
    except Exception as e:
        logging.error('Error loading credentials: %s', e)
        logging.error('Run google-oauthlib-tool to initialize '
                      'new OAuth 2.0 credentials.')
        return

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
    updater.dispatcher.add_handler(CommandHandler('ranking', ranking))
    updater.dispatcher.add_handler(ChatMemberHandler(greet_chat_members, ChatMemberHandler.CHAT_MEMBER))
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, assistant))
    updater.dispatcher.add_error_handler(error)
    updater.job_queue.run_repeating(notify_assignees, 900, context=updater.bot)

    grpc_channel = google.auth.transport.grpc.secure_authorized_channel(credentials, http_request, api_endpoint)
    logging.info('Connecting to %s', api_endpoint)

    global ASSISTANT
    ASSISTANT = TextAssistant(lang, get_device_model_id(), get_project_id(), grpc_channel, grpc_deadline)

    updater.start_polling()
    updater.idle()
    DATABASE.close()


if __name__ == '__main__':
    main()
