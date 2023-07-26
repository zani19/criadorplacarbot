import os
from telebot import types
from dotenv import load_dotenv

load_dotenv()

VERSION = "0.7"
LOG_FOLDER = "log"
LOG_FILE = "criadorplacarbot.log"
MAX_MESSAGES_PER_SECOND = 4
FONT_FILE_NAME = "LiberationSans-Regular.ttf"
NAME_MIN = 3
NAME_MAX = 80
STATE_FINAL = 99
WAITING_PHOTO_STATE = 100
OFFSET = int(os.environ.get("OFFSET", "1"))  # depende da fonte

AGUARDANDO_FOTO = "aguardando a foto da partida"
GERANDO_IMAGEM = "criando a imagem, pode demorar alguns segundos ..."
TIPO_INVALIDO = ("O tipo de jogo deve ser 'simples', "
                 "'duplas' ou 'torneio simples'")
DESEJA_ENVIAR_FOTO = ("deseja enviar a foto da partida? (sim / não)\n"
                      "A imagem com o placar será juntada com a foto enviada")
ENVIE_FOTO = "envie a foto da partida"
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
           f"Versão {VERSION}\n"
           f"Criado por Lucas Pinheiro\n")

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
tipoItem3 = types.KeyboardButton('Torneio Simples')
tipoMarkup.add(tipoItem1, tipoItem2, tipoItem3)

yesNoMarkup = types.ReplyKeyboardMarkup(row_width=2)
yesNo1 = types.KeyboardButton('Sim')
yesNo2 = types.KeyboardButton('Não')
yesNoMarkup.add(yesNo1, yesNo2)

defaultMarkup = types.ReplyKeyboardRemove(selective=False)
