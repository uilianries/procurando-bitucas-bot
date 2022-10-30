#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import json
import random
import configparser
import sys

from datetime import datetime
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from dateutil.parser import parse
from random import randrange
import feedparser
import click
import pytz
from peewee import Model, SqliteDatabase, IntegerField, BooleanField
from google.assistant.embedded.v1alpha2 import embedded_assistant_pb2
from google.assistant.embedded.v1alpha2 import embedded_assistant_pb2_grpc
import google.auth.transport.grpc
import google.auth.transport.requests
import google.oauth2.credentials


BITUCAS_UNDER_MAINTENANCE = os.getenv("BITUCAS_UNDER_MAINTENANCE", False)
BITUCAS_DRY_RUN = os.getenv("BITUCAS_DRY_RUN", False)
BITUCAS_LOGGING_LEVEL = os.getenv("BITUCAS_LOGGING_LEVEL", 10)
CONFIG_FILE = os.getenv("PB_CONFIG", "/etc/bitucas.conf")
ASSISTANT_API_ENDPOINT = 'embeddedassistant.googleapis.com'
DEFAULT_GRPC_DEADLINE = 60 * 3 + 5
TELEGRAM_TOKEN = None
DATABASE_PATH = os.getenv("PB_DATABASE", '/home/orangepi/.pb/pb.sqlite')
DATABASE = SqliteDatabase(DATABASE_PATH)
DEVICE_MODEL_ID = None
PROJECT_ID = None
CREDENTIALS_CONTENT = None
ASSISTANT = None
LAST_NOTIFIED = None
NOTIFICATION_INTERVAL = 60 * 5


class BaseModel(Model):
    class Meta:
        database = DATABASE


class ChatId(BaseModel):
    chatid = IntegerField(unique=True)
    voice = BooleanField(default=False)


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=BITUCAS_LOGGING_LEVEL)
logger = logging.getLogger(__name__)

sao_paulo_tz = pytz.timezone("America/Sao_Paulo")


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
    "Ao invés de importunar, vai dar a meia-hora de bunda!",
    "Na vida, duas coisas são certas, o seu chifre arrastando no chão, e alguém com uma pergunta sem sentido!",
    "Ocorreu um erro, sua pergunta foi tão sem sentido que o servidor pediu ajuda pro Diarorim Doidão",
    "Supunhetamos envaginemos!",
    "Poderia repetir a pergunta, por favor? Tenho dificuldade em compreender gente burra.",
    "Vou chamar o IBAMA pra te estudar!",
    "Liguei pro Butantan pra te cadastrar como espécie rara!",
    "Eu não sou muito boa em elogiar as pessoas, mas pra xingar eu sou uma maravilha.",
    "Hoje está difícil, vou ter que pagar um Uber pra você ir se fuder!",
    "O dia em que a sua opnião for pizza, eu ligo pra pedir!",
    "Vá chupar um canavial de rola!",
    "Estou ocupada minerando Bituca coin, a cryptocueca do Guerreirinho.",
    "Eu pedi pra nascer burra, mas você parece que ajoelhou e implorou!",
    "Me faça um favor, vá coçar o seu cu com um serrote ...",
    "Você é tão desqualificado, que já pode virar podcaster!",
    "Eu não sei, mas vou fazer uma Vakinha pra te dar um cérebro novo.",
    "Pesquise no xvideos, categoria: Bitucas gozadas",
    "Não sei, mas você conhece o Mário?",
    "Não sei, mas você conhece a Paula?",
    "Você é uma mistura de mal com atraso e pitadas de burrice",
    "Você é muito engraçado, vai tomar no cu!",
    "Desculpe, minha CPU está em 100%, estou processando os pedidos de novos episódios",
    "Desculpe, minha CPU está em 100%, não param de chegar pedidos para o Dãozinho voltar!",
    "Isso é bullying, vou chamar o IBAMA pra te recolher.",
    "Não sei, mas qual o episódio do Procurando Bitucas que você mais gosta?",
    "Não sei, mas já assistiu o Procurando Bitucas no XVideos?",
    "Não sei, mas já se inscreveu no Only Haters?",
    "Não sei, mas já contribuiu com a cachaça do Dono na Vakinha?",
    "Estou ocupada, ouvindo Procurando Bitucas ... Aliás, OUVÃO!",
    "Estou ocupada, assistindo o Dono apresentar como ser um Demo Coach.",
    "Estou ocupada, assistindo o Dãozinho sair da geladeira pra gravar um novo episódio",
]


GREETINGS_QUOTES = [
    "Bem-vindo ao Procurando Bitucas {}! Se está procurando ajuda para parar de fumar disque 136.",
    "Bem-vindo ao Procurando Bitucas {}! Tente ficar por pelo menos 1 minuto antes de sair do grupo, nosso recorde é de 7 segundos.",
    "Bem-vindo ao Procurando Bitucas {}! Você acabar de adquirir o kit bituqueiro, que acompanha uma regata suada e um óculos 4D.",
    "Bem-vindo ao Procurando Bitucas {}! Se inscreva no Only Haters também e nos odeie por apenas $15 USD ao mês.",
    "Bem-vindo ao Procurando Bitucas {}! Em instantes você será recebido pelo Dono ou pelo Guerreirinho.",
    "Bem-vindo ao Procurando Bitucas {}! Sou o bot de relações humanas, minha missão é minerar bitcoin no seu celular, então não feche o Telegram.",
    "Bem-vindo ao Procurando Bitucas {}! Não somos um grupo de controle de tabagismo, mas fazemos mais mal que drogas pesadas.",
    "Bem-vindo ao Procurando Bitucas {}! Por favor, se for sair em 1 minuto, ao menos mande um nudes antes.",
    "Bem-vindo ao Procurando Bitucas {}! Se você entrou por engano, lembre-se que não somos grupo anti-tabagista.",
    "Bem-vindo ao Procurando Bitucas {}! Espero que você não seja outra conta fake tentando vender crypto moeda aqui no grupo",
    "Bem-vindo ao Procurando Bitucas {}! Responda a pergunta pra provar que você não é um bot: Você conhece o Mário?",
    "Bem-vindo ao Procurando Bitucas {}! Este é o SAC do pior podcast da podosféra!",
]


GOODBYE_QUOTES = [
    "{} nos deixou, pelo menos um soube a hora certa de parar",
    "{} saiu tarde, espero que não volte",
    "{} adeus!",
    "Acabamos de perder o(a) {}. Alguém xingue no Twitter.",
    "{} se desconectou do grupo. Quem será o próximo?",
    "{}, mas já?!",
    "Perdemos o(a) {}. Que pena, estava prestes a clonar o chip dele(a)!",
    "Já vai tarde {}!",
    "Adiós {}! Queria ganhar 1 dólar pra cada pangaré que sai desse grupo.",
    "Informo que {} foi recolhido pelo IBAMA.",
    "{} tomou uma decisão inteligente",
    "{} vazou antes ver o Guerreirinho pelado, através do óculos 4D",
]

COACH_QUOTES = [
    "Nunca caminhe sem um documento nas mãos. Pessoas com documentos em uma das mãos parecem funcionários ocupadíssimos que se dirigem para reuniões importantes. #democouch",
    "Sempre leve algum material para casa, isso causa a falsa impressão de que você trabalha mais horas do que você costuma trabalhar. #democouch",
    "Tenha uma mesa bagunçada. Quando sua mesa está bagunçada parece que você está trabalhando duramente. #democouch",
    "Construa pilhas enormes de documentos em torno de seu espaço de trabalho para parecer ocupado. #democouch",
    "Ao observador, o trabalho do ano passado parece o mesmo que o trabalho de hoje; é o volume que conta. Se você souber que alguém está vindo à sua mesa finja que está procurando algum papel. #democouch",
    "Nunca responda ao seu telefone se você tiver o correio de voz. As pessoas não te ligam para te dar nada além de mais trabalho. #democouch",
    "Selecione todas suas chamadas sempre através do correio de voz. #democouch",
    "Se alguém deixar uma mensagem do correio de voz para você e se for para trabalho, responda durante a hora do almoço quando você sabe que eles não estão lá. #democouch",
    "Você deve estar sempre parecendo impaciente e irritado, para dar ao seu chefe a impressão de que você está realmente ocupado. #democouch",
    "Sempre deixe o escritório mais tarde, especialmente se o seu chefe estiver por perto. #democouch",
    "Sempre passe na frente da sala do seu Chefe quando estiver indo embora. #democouch",
    "Programe os e-mails importantes pare serem enviados bem tarde (por exemplo 21:35, 6:00, etc…) e durante feriados e finais de semana. #democouch",
    "Fale sozinho quando tiver muita gente por perto, dando a impressão de que você está sob pressão extrema. #democouch",
    "Empilhar documentos em cima da mesa não é o bastante. Ponha vários livros no chão. (os manuais grossos do computador são melhores ainda). #democouch",
    "Procure no dicionário palavras difíceis. Construa frases e use-as quando estiver conversando com o seu chefe. Lembre-se: ele não tem que entender o que você diz, desde que o que você diga dê a entender de que você está certo. #democouch",
    "Querido Papai Noel. Nesse natal eu queria um mindset de filho da puta para poder derrubar o meu chefe. #democouch",
    "Mensagem urgente de WhatsApp: Responda 3h depois que só prioriza ferramentas do trabalho. #democouch",
    "Mensagem urgente do trabalho: Responda 2h depois que estava numa ligação no WhatsApp. #democouch",
    "Mais dicas no livro Demo Couch: Infernizando seu chefe no home office. #democouch",
    "Nesse verão não deixe de beber muita água no trabalho. Não por causa da saúde, mas sim para poder ir ao banheiro sempre que um problema aparecer. #democouch",
    "Bora Timeee!!! Não deixe ninguém falar que vc é fracassado. Essa é sua jornada. Seja proativo, e fale antes. #democouch",
    "Bora timeeeeee!!! Essas casas não serão desapropriadas sozinhas. Bora terraplanar esse mindset derrotista e construir duas torres de auto estima. #democouch",
    "Dicas Home Office: marque reunião de 2 horas, resolva em 30 minutos, fique logado na sala pra trancar sua agenda. Responda que está em reunião e se cuide. #democouch",
    "Bora timeee!!! Se o Instagram caiu, tire foto do seu temake, imprima e mande por correio. Seja menos fazendo mais. #democouch",
    "Isso na privada não são suas fezes, é o reflexo da sua cara expelindo esse mindset modorrento. Escove os dentes e grite no espelho: 'EU SOU O ROCKY BALBOA'. #democouch",
    "Bora timeeee!!! A Faria Lima não anda sozinha. Seja o Redbull da sua vida!!! #democouch",
    "Bora Time!!!!! O jogo tá ganho, mas vamos pra cima fazer mais um gol!!! Goleiro que não franga é pq não foi pra bola!!! #democouch",
    "Vamo timeeee!!! Bora resignificar ASAP essa serotonina em Taffman-E e disruptivar todo esse mindset modorrento. #democouch",
    "Bora Timeeee!!!! Seja seu próprio Facebook e viralize esse mindset mequetrefe. #democouch",
    "Timeeee, quero ver todo mundo com o tridente na mão que hj está o inferno puro. Seja o protagonista nessa porra de filme preto e branco que é sua vida. #democouch",
    "Lute como nunca, perca como sempre. #democouch",
    "Não deixe uma frase motivacional melhorar o seu dia de merda. #democouch",
    "Você não pode mudar o seu passado, mas pode estragar o seu futuro! #democouch",
    "Se foi ruim ontem, fique tranquilo que hoje será pior. #democouch",
    "Vamos levantar? A vida não consegue te derrubar com você deitado. #democouch",
    "Não sabendo que era impossível, foi lá e soube. #democouch",
    "Só dará errado se você tentar. #democouch",
    "Uma grande jornada termina com uma bela derrota. #democouch",
    "O não você já tem, agora falta buscar a humilhação. #democouch",
    "Se alguém te ofendeu sem você merecer, volte lá e mereça! #democouch",
    "Seja o protagonista do seu fracasso. #democouch",
    "Escolha lugares para almoçar que só dê pra ir de carro, que tenha filas longas e que em média o prato chegue 30 minutos depois. Jamais, leve comida de casa, jamais. Fique o mais longe possível do ambiente de trabalho. #democouch"
]


def send_message(context, chat_id, text):
    logger.debug(f"[{chat_id}] {text}")
    if not BITUCAS_DRY_RUN:
        context.bot.send_message(chat_id=chat_id, text=text)


def greetings(update, context):
    message = random.choice(GREETINGS_QUOTES)
    cid = update.message.chat.id
    for member in update.message.new_chat_members:
        send_message(chat_id=cid, text=message.format(member.name))


def goodbye(update, context):
    message = random.choice(GOODBYE_QUOTES)
    cid = update.message.chat.id
    member = update.message.left_chat_member.name
    send_message(chat_id=cid, text=message.format(member))


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
        send_message(cid, display_text)
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
                send_message(cid, display_text)
            else:
                send_message(cid, get_error_message())
        else:
            send_message(cid, "Você me mencionou, mas não disse o que quer.")


def get_error_message():
    return random.choice(ERROR_QUOTES)


def start(update, context):
    send_message(chat_id=update.message.chat_id, text='Olá! Procurando pelo pior podcast das podosfera?\nAcesse http://procurandobitucas.com/')


def episodios(update, context):
    send_message(chat_id=update.message.chat_id,
                             text="Todos os episódios: http://procurandobitucas.com/podcast/episodios/")


def twitter(update, context):
    send_message(chat_id=update.message.chat_id,
                             text="Twitter oficial do PB: https://twitter.com/procurabitucas")


def instagram(update, context):
    send_message(chat_id=update.message.chat_id,
                             text="Instagram oficial do PB: https://www.instagram.com/procurandobitucas")


def spotify(update, context):
    send_message(chat_id=update.message.chat_id,
                             text="Ouvir o PB no Spotify: https://open.spotify.com/show/79cz6YQpsKETIZOeHADXeD?si=Pi1YuzU0Tx-d-AfADSYpvg")


def apple(update, context):
    send_message(chat_id=update.message.chat_id,
                             text="Ouvir o PR no Apple Podcast: https://itunes.apple.com/br/podcast/procurando-bitucas-um-podcast/id1336239884?mt=2&ls=1")


def deezer(update, context):
    send_message(chat_id=update.message.chat_id,
                             text="Ouvir o PR no Deezer: https://www.deezer.com/br/show/520392")


def dono(update, context):
    send_message(chat_id=update.message.chat_id,
                             text="Quem é o dono do PB: https://twitter.com/washi_sena")


def guerreirinho(update, context):
    send_message(chat_id=update.message.chat_id,
                             text="Quem é o host do PB: https://twitter.com/alcofay2k")

def fotografo(update, context):
    send_message(chat_id=update.message.chat_id,
                             text="Quem é o fotógrafo do PB: https://twitter.com/mmessiasjunior")


def telegram(update, context):
    send_message(chat_id=update.message.chat_id,
                             text="Grupo oficial do PB no Telegram: https://t.co/vY2s8UZwLQ?amp=1")


def whatsapp(update, context):
    send_message(chat_id=update.message.chat_id,
                             text="Não tem grupo de Zap Zap, use o /telegram")


def xvideos(update, context):
    send_message(chat_id=update.message.chat_id,
                             text="Canal no XVideos foi derrubado por excesso de acessos, mas você pode assistir pelo óculos 4D.")


def ultimo(update, context):
    rss_feed = feedparser.parse("http://procurandobitucas.com/podcast/feed/podcast/")
    last_ep = rss_feed["entries"][0]
    send_message(chat_id=update.message.chat_id,
                             text="Último episódio disponível: {} - {}".format(last_ep["title"], last_ep["link"]))


def error(update, context):
    logger.warning('Ops! "%s" deu erro "%s"', update, context.error)


def help(update, context):
    send_message(chat_id=update.message.chat_id,
                             text="Use / pra listar os comandos ou utilize o seu óculos 4D!")


def inscritos(update, context):
    send_message(chat_id=update.message.chat_id,
                             text="Computei uma legião aproximada em {} fãs!".format(randrange(3000000000, 4000000000)))


def ranking(update, context):
    send_message(chat_id=update.message.chat_id,
                             text="Acesse https://chartable.com/podcasts/procurando-bitucas para obter a posição atual."
                             "\nNão esqueça de falar mal dos outros podcasts da categoria hobbies")


def demo_couch(update, context):
    message = random.choice(COACH_QUOTES)
    send_message(chat_id=update.message.chat_id,
                             text=message)


def notificar(update, context):
    if is_subscribed(update.message.chat_id):
        logging.info("User subscribed again: {}".format(update.message.from_user.username))
        send_message(chat_id=update.message.chat_id, text="Você já está inscrito para receber novos episódios.")
        return

    logging.info("User subscribed: {}".format(update.message.from_user.username))
    send_message(chat_id=update.message.chat_id, text="Você será notificado quando sair um novo episódio!")
    add_chat_id(update.message.chat_id)


def notify_assignees(context):
    global LAST_NOTIFIED
    rss_feed = feedparser.parse("http://procurandobitucas.com/podcast/feed/podcast/")
    last_ep = rss_feed["entries"][0]
    date = last_ep["published"]
    logger.info("Last ep date: {}".format(date))

    parsed_date = parse(date)
    now = datetime.now(sao_paulo_tz)

    # Demo Couch every Monday. 10:00 10:15
    if now.weekday() == 0 and now.hour == 10 and (0 <= now.minute <= 15):
        message = random.choice(COACH_QUOTES)
        for entry in ChatId.select():
            send_message(chat_id=entry.chatid, text=message)

    if now.day == parsed_date.day and now.month == parsed_date.month and now.year == parsed_date.year:
        # already notified today
        if LAST_NOTIFIED is not None and LAST_NOTIFIED.year == now.year and LAST_NOTIFIED.month == now.month and LAST_NOTIFIED.day == now.day:
            return

        LAST_NOTIFIED = now

        for entry in ChatId.select():
            logger.info("New episode: {} - Send to {}".format(date, entry.chatid))
            send_message(chat_id=entry.chatid, text="Novo episódio - {}: {}".format(last_ep["title"], last_ep["link"]))


def parar(update, context):
    if is_subscribed(update.message.chat_id):
        logging.info("User unsubscribed: {}".format(update.message.from_user.username))
        send_message(chat_id=update.message.chat_id,
                                 text='Você não receberá novas notificações de episódios.')
        remove_chat_id(update.message.chat_id)
    else:
        logging.info("User unsubscribed again: {}".format(update.message.from_user.username))
        send_message(chat_id=update.message.chat_id,
                                 text='Você já não está inscrito para receber notficações.')


def create_db():
    if not os.path.exists(DATABASE_PATH):
        DATABASE.connect()
        DATABASE.create_tables([ChatId])


def add_chat_id(chat_id):
    ChatId.insert(chatid=chat_id).on_conflict_ignore().execute()


def remove_chat_id(chat_id):
    query = ChatId.delete().where(ChatId.chatid == chat_id)
    query.execute()


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
def procurando_bitucas(api_endpoint, credentials_path, lang, verbose, grpc_deadline, *args, **kwargs):
    if get_telegram_token() is None:
        logger.error("TELEGRAM TOKEN is Empty.")
        raise ValueError("TELEGRAM_TOKEN is unset.")

    DATABASE.connect(reuse_if_open=True)
    updater = Updater(get_telegram_token(), use_context=True)
    logging.info("TELEGRAM: {}".format(get_telegram_token()))

    if BITUCAS_UNDER_MAINTENANCE:
        logging.warning("Procurando Bitucas is under maintenance. Exiting now.")
        sys.exit(503)

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
    updater.dispatcher.add_handler(CommandHandler('democouch', demo_couch))
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, assistant))
    updater.dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, greetings))
    updater.dispatcher.add_handler(MessageHandler(Filters.status_update.left_chat_member, goodbye))
    updater.dispatcher.add_error_handler(error)
    updater.job_queue.run_repeating(notify_assignees, NOTIFICATION_INTERVAL, context=updater.bot)

    grpc_channel = google.auth.transport.grpc.secure_authorized_channel(credentials, http_request, api_endpoint)
    logging.info('Connecting to %s', api_endpoint)

    global ASSISTANT
    ASSISTANT = TextAssistant(lang, get_device_model_id(), get_project_id(), grpc_channel, grpc_deadline)

    updater.start_polling()
    updater.idle()
    DATABASE.close()


def show_configuration():
    telegram_token = str(get_telegram_token())[:8]
    logger.info(f"TELEGRAM TOKEN: {telegram_token}")
    devide_model_id = get_device_model_id()
    logger.info(f"DEVICE MODEL ID: {devide_model_id}")
    project_id = get_project_id()
    logger.info(f"PROJECT ID: {project_id}")
    logger.info(f"UNDER MAINTENANCE: {BITUCAS_UNDER_MAINTENANCE}")
    logger.info(f"DRY RUN: {BITUCAS_DRY_RUN}")
    logger.info(f"CONFIG FILE: {CONFIG_FILE}")
    logger.info(f"DATABASE FILE: {DATABASE_PATH}")


def main():
    show_configuration()
    create_db()
    procurando_bitucas()


if __name__ == '__main__':
    main()
