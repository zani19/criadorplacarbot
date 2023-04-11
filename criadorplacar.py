import telebot
from telebot import types
import io
import os
import re
from PIL import Image, ImageDraw, ImageFont
import time
from typing import NamedTuple
import copy
import logging
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

load_dotenv()

# TODO
# import inotify.adapters

# constants
VERSION = "0.5"
LOG_FOLDER = "log"
LOG_FILE = "criadorplacarbot.log"
# LOG_FILE_MAX_SIZE = 10000000 # 10 mb # TODO with inotify
MAX_MESSAGES_PER_SECOND = 4
# FONT_FILE_NAME = "cour.ttf"
FONT_FILE_NAME = "LiberationSans-Regular.ttf"
NAME_MIN = 3
NAME_MAX = 80
OFFSET = int(os.environ.get("OFFSET"))  # depende da fonte


TIPO_INVALIDO = "O tipo de jogo deve ser 'simples' ou 'duplas'"
JOGADOR_INVALIDO = (f"O nome de um jogador deve possuir"
                    f"entre {NAME_MIN} e {NAME_MAX} caracteres")
WELCOME = (f"Seja bem-vindo ao CriadorPlacarBot! Este bot tem como "
           f"objetivo gerar imagens com os dados de um jogo válido pelo "
           f"ranking da OPEN. Ele foi desenvolvido de forma independente e "
           f"não possui vínculo oficial com o ranking. O objetivo é apenas "
           f"facilitar a geração da imagem.\n\n"
           f"Por enquanto, não há verificação de dados, como locais ou nomes "
           f"de jogadores. É possível usar letras maiúsculas ou minúsculas em "
           f"todos os campos (e em alguns casos, até botões de respostas "
           f"rápidas).\n\n"
           f"Para iniciar, use o comando /placar. Para interromper o processo "
           f"atual, use o comando /cancelar.\n\n"
           f"Para ver esta mensagem de ajuda novamente, basta usar o comando "
           f"/help.\n\n"
           f"Versão {VERSION}")


# boxes
# configurado para funcionar com Anchor="mm"
class FieldDimensions(NamedTuple):
    maxWidth: int
    maxHeight: int
    x: int
    y: int


""" TENISTA_1 = FieldDimensions(440, 69, 616, 190)
TENISTA_2 = FieldDimensions(440, 69, 616, 315)
CAT_1 = FieldDimensions(86, 77, 951, 192)
CAT_2 = FieldDimensions(86, 77, 951, 315)
PLACAR_1 = FieldDimensions(245, 130, 594, 603)
PLACAR_2 = FieldDimensions(245, 130, 594, 837)
TIEBREAK_1 = FieldDimensions(140, 130, 888, 603)
TIEBREAK_2 = FieldDimensions(140, 130, 888, 837)
LOCAL = FieldDimensions(530, 68, 674, 994) """

simplesDimensions = {
    "TENISTA_1": FieldDimensions(440, 69, 616, 190),
    "TENISTA_2": FieldDimensions(440, 69, 616, 315),
    "CAT_1": FieldDimensions(86, 77, 951, 192),
    "CAT_2": FieldDimensions(86, 77, 951, 315),
    "PLACAR_1": FieldDimensions(245, 130, 594, 603),
    "PLACAR_2": FieldDimensions(245, 130, 594, 837),
    "TIEBREAK_1": FieldDimensions(140, 130, 888, 603),
    "TIEBREAK_2": FieldDimensions(140, 130, 888, 837),
    "LOCAL": FieldDimensions(530, 68, 674, 994)
}

duplasDimensions = {
    "DUPLA_1": FieldDimensions(384, 47, 357, 123),
    "DUPLA_2": FieldDimensions(384, 47, 357, 205),
    "CAT_1": FieldDimensions(57, 50, 604, 126),
    "CAT_2": FieldDimensions(57, 50, 685, 126),
    "CAT_3": FieldDimensions(57, 50, 604, 200),
    "CAT_4": FieldDimensions(57, 50, 685, 200),
    "PLACAR_1": FieldDimensions(98, 94, 388, 395),
    "PLACAR_2": FieldDimensions(98, 94, 391, 548),
    "TIEBREAK_1": FieldDimensions(98, 94, 582, 395),
    "TIEBREAK_2": FieldDimensions(98, 94, 584, 548),
    "LOCAL": FieldDimensions(355, 50, 441, 650)  # 196
}

# set up logging
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[
        RotatingFileHandler(os.path.join(LOG_FOLDER, LOG_FILE),
                            maxBytes=1_000_000, backupCount=5),
        logging.StreamHandler()
    ]
)

# start
logger = logging.getLogger(__name__)
last_message_time = {}
bot = telebot.TeleBot(os.environ.get("BOT_KEY"))
user_info = {}
state = {}


def validate_tipo(text):
    s = text.upper()
    return s in {"SIMPLES", "DUPLAS"}


def validate_name(text):
    return NAME_MIN <= len(text) <= NAME_MAX


def validate_local(text):
    return 1 <= len(text) <= 100


def validate_cat(text):
    s = text.upper()
    return s in {"C", "B", "A", "S", "SS"}


def validate_score(text):
    length = len(text)

    if length < 2:
        return False
    elif length == 2:
        return text in {"60", "61", "62", "63", "64", "75"}
    else:
        pattern = r'^76\(\d+\)$'
        return re.match(pattern, text) is not None


# @bot.message_handler(commands=['help', 'start'])
@bot.message_handler(func=lambda message: True, commands=['help', 'start'])
def send_welcome(message):
    user_id = message.from_user.id
    current_time = time.time()
    if user_id in last_message_time:
        time_since_last_message = current_time - last_message_time[user_id]
        if time_since_last_message < 1.0 / MAX_MESSAGES_PER_SECOND:
            bot.send_message(
                message.chat.id,
                (f"Muitas mensagens dentro de um curto período de tempo."
                 f" Capacidade de processamento apenas de"
                 f" {MAX_MESSAGES_PER_SECOND} mensagens por segundo")
            )
            return
    last_message_time[user_id] = current_time

    bot.reply_to(message, WELCOME)


@bot.message_handler(commands=['cancelar'])
def handle_cancel(message):
    user_id = message.from_user.id
    current_time = time.time()
    if user_id in last_message_time:
        time_since_last_message = current_time - last_message_time[user_id]
        if time_since_last_message < 1.0 / MAX_MESSAGES_PER_SECOND:
            bot.send_message(
                message.chat.id,
                (f"Muitas mensagens dentro de um curto período de tempo."
                 f" Capacidade de processamento apenas de"
                 f" {MAX_MESSAGES_PER_SECOND} mensagens por segundo")
            )
            return
    last_message_time[user_id] = current_time

    if not state or message.chat.id not in state or state[message.chat.id] < 0:
        bot.send_message(
            message.chat.id, "Ainda não há processo para ser cancelado "
            ", inicie um com o comando /placar"
        )
        return

    state[message.chat.id] = -1
    bot.send_message(
        message.chat.id, "Processo cancelado. "
        "Você pode iniciar um novo o comando /placar"
    )


def max_font(text, width, height):
    font_size = 10
    past_font = ImageFont.truetype(FONT_FILE_NAME, font_size)
    past_bbox = past_font.getbbox(text)

    while True:
        font = ImageFont.truetype(FONT_FILE_NAME, font_size + 1)
        bbox = font.getbbox(text)
        if bbox[2] - bbox[0] > width or bbox[3] - bbox[1] > height:
            break
        font_size += 1
        past_font = copy.deepcopy(font)
        past_bbox = copy.deepcopy(bbox)

    return past_font, past_bbox


def draw_text(field, text, draw):
    font, bbox = max_font(text, field.maxWidth, field.maxHeight)
    # print(text, field.x, field.y, bbox)

    x = field.x
    y = field.y + OFFSET  # + (field.maxHeight - bbox[3])/2
    draw.text((x, y), text, font=font, fill=(0, 0, 0), anchor="mm")


def create_image(chat_id):
    img = Image.open("ranking.jpg")
    draw = ImageDraw.Draw(img)

    text = user_info[chat_id]["player1"].title()
    draw_text(simplesDimensions["TENISTA_1"], text, draw)

    text = user_info[chat_id]["player2"].title()
    draw_text(simplesDimensions["TENISTA_2"], text, draw)

    text = user_info[chat_id]["cat1"].upper()
    draw_text(simplesDimensions["CAT_1"], text, draw)

    text = user_info[chat_id]["cat2"].upper()
    draw_text(simplesDimensions["CAT_2"], text, draw)

    score = user_info[chat_id]["score"]

    text = score[:1]
    draw_text(simplesDimensions["PLACAR_1"], text, draw)

    text = score[1:2]
    draw_text(simplesDimensions["PLACAR_2"], text, draw)

    if len(score) > 2:
        match = re.search(r"\((\d+)\)", score)
        tie2 = int(match.group(1))
        tie1 = 7

        if tie2 > 5:
            tie1 = tie2 + 2

        # tiebreak 1
        text = str(tie1)
        draw_text(simplesDimensions["TIEBREAK_1"], text, draw)

        # tiebreak 2
        text = str(tie2)
        draw_text(simplesDimensions["TIEBREAK_2"], text, draw)

    # local
    text = user_info[chat_id]["local"].upper()
    draw_text(simplesDimensions["LOCAL"], text, draw)

    # Save the image
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    bot.send_photo(chat_id=chat_id, photo=img_byte_arr)

    logger.info(
        (f"photo sent, chat_id={chat_id}, "
         f"user_info={user_info[chat_id]}")
    )


def create_image_duplas(chat_id):
    img = Image.open("ranking-duplas.jpg")
    draw = ImageDraw.Draw(img)

    text = user_info[chat_id]["player1"].title() + \
        "/" + user_info[chat_id]["player2"].title()

    draw_text(duplasDimensions["DUPLA_1"], text, draw)

    text = user_info[chat_id]["player3"].title() + \
        "/" + user_info[chat_id]["player4"].title()

    draw_text(duplasDimensions["DUPLA_2"], text, draw)

    text = user_info[chat_id]["cat1"].upper()
    draw_text(duplasDimensions["CAT_1"], text, draw)

    text = user_info[chat_id]["cat2"].upper()
    draw_text(duplasDimensions["CAT_2"], text, draw)

    text = user_info[chat_id]["cat3"].upper()
    draw_text(duplasDimensions["CAT_3"], text, draw)

    text = user_info[chat_id]["cat4"].upper()
    draw_text(duplasDimensions["CAT_4"], text, draw)

    score = user_info[chat_id]["score"]

    text = score[:1]
    draw_text(duplasDimensions["PLACAR_1"], text, draw)

    text = score[1:2]
    draw_text(duplasDimensions["PLACAR_2"], text, draw)

    if len(score) > 2:
        match = re.search(r"\((\d+)\)", score)
        tie2 = int(match.group(1))
        tie1 = 7

        if tie2 > 5:
            tie1 = tie2 + 2

        # tiebreak 1
        text = str(tie1)
        draw_text(duplasDimensions["TIEBREAK_1"], text, draw)

        # tiebreak 2
        text = str(tie2)
        draw_text(duplasDimensions["TIEBREAK_2"], text, draw)

    # local
    text = user_info[chat_id]["local"].upper()
    draw_text(duplasDimensions["LOCAL"], text, draw)

    # Save the image
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    bot.send_photo(chat_id=chat_id, photo=img_byte_arr)

    logger.info(
        (f"photo sent, chat_id={chat_id}, "
         f"user_info={user_info[chat_id]}")
    )


""" markup = telebot.service_utils.quick_markup(
    {'text': 'Press me', 'callback_data': 'press'},
    {'text': 'Press me too', 'callback_data': 'press_too'}
)

inlineMarkup = types.InlineKeyboardMarkup()
inlineMarkup.rows = 2
catInlineItem1 = types.InlineKeyboardButton('Simples')
catInlineItem2 = types.InlineKeyboardButton('Duplas')
inlineMarkup.add(catInlineItem1, catInlineItem2) """

catMarkup = types.ReplyKeyboardMarkup(row_width=2)
catItem1 = types.KeyboardButton('C')
catItem2 = types.KeyboardButton('B')
catItem3 = types.KeyboardButton('A')
catItem4 = types.KeyboardButton('S')
catItem5 = types.KeyboardButton('SS')
catMarkup.add(catItem1, catItem2, catItem3, catItem4, catItem5)

tipoMarkup = types.ReplyKeyboardMarkup(row_width=1)
tipoItem1 = types.KeyboardButton('Simples')
tipoItem2 = types.KeyboardButton('Duplas')
tipoMarkup.add(tipoItem1, tipoItem2)

defaultMarkup = types.ReplyKeyboardRemove(selective=False)

initialHandler = [
    "Selecione a categoria do jogo (simples ou duplas)",
    TIPO_INVALIDO,
    validate_tipo,
    "tipo",
    tipoMarkup
]

stateHandler = [
    (
        "Insira o nome do jogador vencedor",
        JOGADOR_INVALIDO,
        validate_name,
        "player1",
        defaultMarkup
    ),
    (
        "Insira a categoria do jogador vencedor (C, B, A, S ou SS)",
        "Categoria Inválida. As categorias válidas são C, B, A, S ou SS",
        validate_cat,
        "cat1",
        catMarkup
    ),
    (
        "Insira o nome do jogador derrotado",
        JOGADOR_INVALIDO,
        validate_name,
        "player2",
        defaultMarkup
    ),
    (
        "Insira a categoria do jogador derrotado (C, B, A, S ou SS)",
        "Categoria Inválida. As categorias válidas são C, B, A, S ou SS",
        validate_cat,
        "cat2",
        catMarkup
    ),
    (
        "Insira o placar do jogo, sempre em referência ao vencedor e apenas "
        "números. Exemplos: 60, 63, 75. Em caso de tiebreak, informe os "
        "pontos do perdedor entre parênteses, exemplos: 76(4), 76(9)",
        "Placar inválido",
        validate_score,
        "score",
        defaultMarkup
    ),
    (
        "Insira o nome do local onde ocorreu o jogo",
        "Local inválido",
        validate_local,
        "local",
        defaultMarkup
    )
]

stateHandlerDuplas = [
    (
        "Insira o nome do Tenista 1 da dupla vencedora",
        JOGADOR_INVALIDO,
        validate_name,
        "player1",
        defaultMarkup
    ),
    (
        "Insira a categoria do Tenista 1 da dupla vencedora "
        "(C, B, A, S ou SS)",
        "Categoria Inválida. As categorias válidas são C, B, A, S ou SS",
        validate_cat,
        "cat1",
        catMarkup
    ),
    (
        "Insira o nome do Tenista 2 da dupla vencedora",
        JOGADOR_INVALIDO,
        validate_name,
        "player2",
        defaultMarkup
    ),
    (
        "Insira a categoria do Tenista 2 da dupla vencedora "
        "(C, B, A, S ou SS)",
        "Categoria Inválida. As categorias válidas são C, B, A, S ou SS",
        validate_cat,
        "cat2",
        catMarkup
    ),
    (
        "Insira o nome do Tenista 1 da dupla derrotada",
        JOGADOR_INVALIDO,
        validate_name,
        "player3",
        defaultMarkup
    ),
    (
        "Insira a categoria do Tenista 1 da dupla derrotada "
        "(C, B, A, S ou SS)",
        "Categoria Inválida. As categorias válidas são C, B, A, S ou SS",
        validate_cat,
        "cat3",
        catMarkup
    ),
    (
        "Insira o nome do Tenista 2 da dupla derrotada",
        JOGADOR_INVALIDO,
        validate_name,
        "player4",
        defaultMarkup
    ),
    (
        "Insira a categoria do Tenista 2 da dupla derrotada "
        "(C, B, A, S ou SS)",
        "Categoria Inválida. As categorias válidas são C, B, A, S ou SS",
        validate_cat,
        "cat4",
        catMarkup
    ),
    (
        "Insira o placar do jogo, sempre em referência à dupla "
        "vencedora e apenas números. Exemplos: 60, 63, 75. "
        "Em caso de tiebreak, informe os "
        "pontos do perdedor entre parênteses, exemplos: 76(4), 76(9)",
        "Placar inválido",
        validate_score,
        "score",
        defaultMarkup
    ),
    (
        "Insira o nome do local onde ocorreu o jogo",
        "Local inválido",
        validate_local,
        "local",
        defaultMarkup
    )
]


@bot.message_handler(commands=['placar'])
def placar(message):
    user_id = message.from_user.id
    current_time = time.time()
    if user_id in last_message_time:
        time_since_last_message = current_time - last_message_time[user_id]
        if time_since_last_message < 1.0 / MAX_MESSAGES_PER_SECOND:
            bot.send_message(
                message.chat.id,
                (f"Muitas mensagens dentro de um curto período de tempo."
                 f" Capacidade de processamento apenas de"
                 f" {MAX_MESSAGES_PER_SECOND} mensagens por segundo")
            )
            return
    last_message_time[user_id] = current_time

    chat_id = message.chat.id
    if state and chat_id in state and state[chat_id] >= 0:
        bot.send_message(
            chat_id=chat_id,
            text="Já existe um processo em andamento. Para começar "
            "um novo primeiramente é necessário cancelar o corrente "
            "com o comando /cancelar"
        )
        return

    state[chat_id] = -1
    bot.send_message(
        chat_id=chat_id,
        text=initialHandler[0],
        reply_markup=initialHandler[4]
    )

    # bot.register_next_step_handler(message, process_player1)


# @bot.message_handler(content_types=['text'])
@bot.message_handler(func=lambda message: True)
def process_inputs(message):

    user_id = message.from_user.id
    current_time = time.time()
    if user_id in last_message_time:
        time_since_last_message = current_time - last_message_time[user_id]
        if time_since_last_message < 1.0 / MAX_MESSAGES_PER_SECOND:
            bot.send_message(
                message.chat.id,
                (f"Muitas mensagens dentro de um curto período de tempo."
                 f" Capacidade de processamento apenas de"
                 f" {MAX_MESSAGES_PER_SECOND} mensagens por segundo")
            )
            return
    last_message_time[user_id] = current_time
    # Your code that handles the message
    # bot.send_message(message.chat.id, "Your message was received!")

    chat_id = message.chat.id
    text = message.text.strip()

    if not state or chat_id not in state or state[chat_id] < -1:
        bot.send_message(chat_id=chat_id, text=WELCOME)
        return

    currentState = state[chat_id]
    # print(f"current state = {currentState}")

    if chat_id not in user_info:
        user_info[chat_id] = {}

    if currentState == -1:
        if (initialHandler[2](text)):
            user_info[chat_id][initialHandler[3]] = text
        else:
            bot.send_message(
                chat_id=chat_id,
                text=initialHandler[1],
                reply_markup=initialHandler[4]
            )
            return

    state_handler = stateHandler
    if "tipo" in user_info[chat_id] and user_info[chat_id]["tipo"].upper() == "DUPLAS":
        state_handler = stateHandlerDuplas

    """if currentState == len(state_handler):
        bot.send_message(
            chat_id=chat_id,
            text="para começar uma nova geração de placar, "
            "use novamente o comando /placar"
        )
        return """

    # print(f"start msg state={currentState}")
    if (state_handler[currentState][2](text)):
        # print("inserting")
        # print(f"key {state_handler[currentState][3]}, text {text}")
        user_info[chat_id][state_handler[currentState][3]] = text
        # print(user_info[chat_id])

        if "tipo" in user_info[chat_id] and user_info[chat_id]["tipo"].upper() == "DUPLAS":
            state_handler = stateHandlerDuplas
        else:
            state_handler = stateHandler

        state[chat_id] += 1

        if currentState + 1 < len(state_handler):
            bot.send_message(
                chat_id=chat_id,
                text=state_handler[currentState + 1][0],
                reply_markup=state_handler[currentState + 1][4]
            )
        else:
            bot.send_message(
                chat_id=chat_id,
                text="criando a imagem, pode demorar alguns segundos ..."
            )
            if user_info[chat_id]["tipo"].upper() == "DUPLAS":
                create_image_duplas(chat_id)
            else:
                create_image(chat_id)

            logger.info(
                (f"state len: {len(state)}\n"
                 f"user_info len: {len(user_info)}")
            )
            
            #state[chat_id] = -1
            state.pop(chat_id)
            # bot.send_message(chat_id=chat_id, text="acabou")

    else:
        bot.send_message(
            chat_id=chat_id,
            text=state_handler[currentState][1],
            reply_markup=state_handler[currentState][4]
        )


logger.info("running...")
bot.infinity_polling()
