import requests
import re
import time
import json
import emojis
import sys
import logging
import logging.handlers as handlers
import paho.mqtt.client as mqtt
from datetime import datetime
from datetime import timedelta

########################################################################################################################
# config
with open('config.json') as config_file:
    config_dict = json.load(config_file)

# mqtt
CLIENT_NAME = config_dict["client"]
BROKER_IP = config_dict["broker"]

# telegram
AUTH_TOKEN = config_dict["auth_token"]
USER_LIST = config_dict["user_list"]
BASE_URL = "https://api.telegram.org/bot{}/".format(AUTH_TOKEN)
UPDATE_URL = BASE_URL + "getUpdates"
SEND_URL = BASE_URL + "sendMessage"
EDIT_URL = BASE_URL + "editMessageText"
TIMEOUT = 1

# regex validazione programma
pattern_orario = re.compile("^(2[0-3]|[01][0-9]):([0-5][0-9])$")
pattern_durata = re.compile("^([1-5]?[0-9])$")

# bot logger
botLogger = logging.getLogger('bot')
botLogger.setLevel(logging.INFO)

# mqtt logger: atom/water atom/flow
mqttLogger = logging.getLogger("mqtt")
mqttLogger.setLevel(logging.INFO)

# formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s','%d/%m/%Y %H:%M:%S')

# bot file handler
botFileLogHandler = handlers.TimedRotatingFileHandler('bot.log', when='midnight')
botFileLogHandler.setLevel(logging.INFO)
botFileLogHandler.setFormatter(formatter)

# mqtt file handler
mqttFileLogHandler = handlers.TimedRotatingFileHandler('mqtt.log', when='midnight')
mqttFileLogHandler.setLevel(logging.INFO)
mqttFileLogHandler.setFormatter(formatter)

# console handler
consoleLogHandler = logging.StreamHandler(sys.stdout)
consoleLogHandler.setLevel(logging.INFO)
consoleLogHandler.setFormatter(formatter)

# bot add handler
botLogger.addHandler(botFileLogHandler)
botLogger.addHandler(consoleLogHandler)

# mqtt add handler
mqttLogger.addHandler(mqttFileLogHandler)
mqttLogger.addHandler(consoleLogHandler)


########################################################################################################################
# telegram bot
def update_bot(current_update_id):
    update_payload = gen_payload_update()

    if current_update_id:
        update_payload["offset"] = current_update_id

    # telegram bot update
    # long polling
    res_dict = requests.post(UPDATE_URL, json=update_payload).json()

    # check risposta
    if res_dict["ok"] and (len(res_dict["result"]) > 0) and res_dict["result"][0]["message"]["chat"]["id"] in USER_LIST:
        update_dict = res_dict["result"][0]
        next_update_id = res_dict["result"][0]["update_id"] + 1
    else:
        update_dict = dict()
        next_update_id = current_update_id

    return update_dict, next_update_id


def elabora_update(update_dict, stato_rubinetto, prog, mqtt_client):
    # chat_id è l'id dell'utente telegram con cui si sta interagendo
    chat_id = update_dict["message"]["chat"]["id"]
    cmd_list = update_dict["message"]["text"].split()

    # command case
    if (len(cmd_list) == 1) and (cmd_list[0] == "/start"):
        botLogger.info("{} -> /start".format(chat_id))
        # stampare riepilogo
        send_msg(gen_payload_start(chat_id, stato_rubinetto, prog))

    elif (len(cmd_list) == 1) and (cmd_list[0] == "/rubinetto"):
        botLogger.info("{} -> /rubinetto".format(chat_id))
        # stampa rubinetto
        send_msg(gen_payload_rubinetto(chat_id, stato_rubinetto))

    elif (len(cmd_list) == 1) and (cmd_list[0] == "/apri_rubinetto"):
        botLogger.info("{} -> /apri_rubinetto".format(chat_id))
        # apre rubinetto
        stato_rubinetto = apri_rubinetto(stato_rubinetto, mqtt_client)
        # notifica
        send_msg(gen_payload_rubinetto(chat_id, stato_rubinetto))

    elif (len(cmd_list) == 1) and (cmd_list[0] == "/chiudi_rubinetto"):
        botLogger.info("{} -> /chiudi_rubinetto".format(chat_id))
        # chiude rubinetto
        stato_rubinetto = chiudi_rubinetto(stato_rubinetto, mqtt_client)
        # notifica
        send_msg(gen_payload_rubinetto(chat_id, stato_rubinetto))

    elif (len(cmd_list) == 1) and (cmd_list[0] == "/programma"):
        botLogger.info("{} -> /programma".format(chat_id))
        # mostra programma
        send_msg(gen_payload_prog(chat_id, prog))

    elif (len(cmd_list) == 3) and (cmd_list[0] == "/nuovo_programma") and pattern_orario.match(cmd_list[1]) and pattern_durata.match(cmd_list[2]):
        botLogger.info("{} -> /nuovo_programmma {} {}".format(chat_id, cmd_list[1], cmd_list[2]))
        # aggiungi/modifica nuovo programma
        prog = aggiorna_programma(prog, orario_str=cmd_list[1], durata=cmd_list[2])
        # mostra programmma aggiornato
        send_msg(gen_payload_prog(chat_id, prog))

    elif (len(cmd_list) == 1) and (cmd_list[0] == "/cancella_programma"):
        botLogger.info("{} -> /cancella_programma".format(chat_id))
        # cancella programma
        prog = aggiorna_programma(prog, orario_str=str(), durata=str())
        # mostra programma aggiornato
        send_msg(gen_payload_prog(chat_id, prog))

    else:
        # messaggio non valido
        botLogger.info("{} -> comando non valido".format(chat_id))
        # mostra messaggio errore
        send_msg(gen_payload_command_error(chat_id))

    return stato_rubinetto, prog


def send_msg(payload):
    res_dict = requests.post(SEND_URL, json=payload).json()
    return res_dict["ok"]


def notifica_utenti(text):
    # notify all telegram user
    for user in USER_LIST:
        send_msg(gen_payload_notifica(user, text))


########################################################################################################################
# telegram bot payloads
def gen_payload_update():
    return {
        "timeout": TIMEOUT,
        "allowed_updates": ["message"]
    }


def gen_payload_start(chat_id, stato_rubinetto, prog):
    return {
        "chat_id": chat_id,
        "text": (
                   "Benvenuto nel sistema di irrigazione!"
                   "\n\n"
                   "<b>rubinetto</b>: <i>{}</i>"
                   "\n\n"
                   "<b>programma</b>: <i>{}</i>\n"
                   "inizio: <i>{}</i>\n"
                   "fine:   <i>{}</i>\n"
                   "durata: <i>{}</i> {}".format(stato_rubinetto, prog["stato"], prog["start_str"], prog["end_str"],
                                                 prog["durata"], "min" if prog["start_str"] else "")
                 ),
        "parse_mode": "HTML"
    }


def gen_payload_rubinetto(chat_id, stato_rubinetto):
    return {
        "chat_id": chat_id,
        "text": "<b>rubinetto</b>: <i>{}</i>".format(stato_rubinetto),
        "parse_mode": "HTML"
    }


def gen_payload_prog(chat_id, prog):
    return {
        "chat_id": chat_id,
        "text": (
            "<b>programma</b>:\n"
            "stato: <i>{}</i>\n"
            "inizio: <i>{}</i>\n"
            "fine:   <i>{}</i>\n"
            "durata: <i>{}</i> {}".format(prog["stato"], prog["start_str"], prog["end_str"], prog["durata"],
                                          "min" if prog["start_str"] else "")
        ),
        "parse_mode": "HTML"
    }


def gen_payload_notifica(chat_id, text):
    return {
        "chat_id": chat_id,
        "text": text
    }


def gen_payload_command_error(chat_id):
    return {
        "chat_id": chat_id,
        "text": (
            "<b>comando non valido</b>"
        ),
        "parse_mode": "HTML"
    }


########################################################################################################################
# rubinetto
def init_rubinetto():
    _rubinetto = "off"
    _portata = "0.0"
    return _rubinetto, _portata


def apri_rubinetto(stato_rubinetto, mqtt_client):
    # apre rubinetto
    if (stato_rubinetto == "off") and pub_msg(mqtt_client, "on"):
        stato_rubinetto = "on"
        # stabilizzazione flusso
        time.sleep(3)
    return stato_rubinetto


def chiudi_rubinetto(stato_rubinetto, mqtt_client):
    # chiude rubinetto
    if (stato_rubinetto == "on") and pub_msg(mqtt_client, "off"):
        stato_rubinetto = "off"
        # stabilizzazione flusso
        time.sleep(3)
    return stato_rubinetto


def check_portata(stato_rubinetto):
    if (stato_rubinetto == "on") and (float(portata) == 0.0):
        botLogger.warning("rubinetto: on >>> acqua: no")
        notifica_utenti(emojis.encode(":warning:problemi al rubinetto! Non sta passando acqua...:warning:"))

    elif (stato_rubinetto == "off") and (float(portata) > 0.0):
        botLogger.warning("rubinetto: off >>> acqua: yes")
        notifica_utenti(emojis.encode(":warning:problemi al rubinetto! Sta passando acqua...:warning:"))


########################################################################################################################
# programma
def init_programma():
    return {
        "start_str": str(),
        "end_str": str(),
        "start_obj": None,
        "end_obj": None,
        "durata": str(),
        "stato": "off"
    }


def aggiorna_programma(prog, orario_str, durata):
    # aggiungi/modifica/cancella
    prog["start_str"] = orario_str
    prog["start_obj"] = datetime.strptime(orario_str, "%H:%M") if orario_str else None
    prog["durata"] = durata
    prog["end_obj"] = prog["start_obj"] + timedelta(minutes=int(prog["durata"])) if orario_str else None
    prog["end_str"] = prog["end_obj"].strftime("%H:%M") if orario_str else str()
    return prog


def gestione_programma(stato_rubinetto, prog, mqtt_client):
    # gestione programma irrigazione
    # controllare se bisogna attivare il programma irrigazione
    # NOTA: qui si notifica a tutti i chat_id registrati/autorizzati! Sono notifiche importanti.
    try:
        # check preliminari
        start_time = prog["start_obj"].time()
        end_time = prog["end_obj"].time()
        now_time = datetime.now().time()

        # caso standard
        if (start_time <= now_time < end_time) and (prog["stato"] == "off"):
            stato_rubinetto, prog = start_programma(stato_rubinetto, prog, mqtt_client)

        # caso standard
        elif (now_time >= end_time) and (prog["stato"] == "on"):
            stato_rubinetto, prog = end_programma(stato_rubinetto, prog, mqtt_client)

        # caso particolare: il programma era in esecuzione e un utente ha chiuso il rubinetto
        #elif (prog["stato"] == "on") and (stato_rubinetto == "off"):
        #    stato_rubinetto, prog = end_programma(stato_rubinetto, prog, mqtt_client)

    except AttributeError:
        # start_obj e end_obj sono None, quindi non è presente un programma
        # caso particolare: l'utente ha cancellato un programma che era in esecuzione
        if prog["stato"] == "on":
            stato_rubinetto, prog = end_programma(stato_rubinetto, prog, mqtt_client)

    return stato_rubinetto, prog


def start_programma(stato_rubinetto, prog, mqtt_client):
    prog["stato"] = "on"
    # notifica inizio programma
    botLogger.info("inizio programma irrigazione")
    notifica_utenti("inizio programma irrigazione")
    # bisogna aprire il rubinetto, cioè inizia programma di irrigazione
    stato_rubinetto = apri_rubinetto(stato_rubinetto, mqtt_client)
    return stato_rubinetto, prog


def end_programma(stato_rubinetto, prog, mqtt_client):
    prog["stato"] = "off"
    # notifica fine programma
    botLogger.info("fine programma irrigazione")
    notifica_utenti("fine programma irrigazione")
    # bisogna chiudere il rubinetto, cioè termina il programma di irrigazione
    stato_rubinetto = chiudi_rubinetto(stato_rubinetto, mqtt_client)
    return stato_rubinetto, prog


########################################################################################################################
# mqtt
def crea_client(name, callbacks, broker):
    # create client instance
    client = mqtt.Client(name)
    # attach callbacks to client
    client.on_connect = callbacks["con"]
    client.on_disconnect = callbacks["dis"]
    client.on_message = callbacks["msg"]
    # connect to a broker
    client.connect(broker)  # bloccante, fino a che non ci si connette ci si blocca qui
    # qui il client è connesso
    # subscribe water flow sensor
    # check return status
    client.subscribe("atom/flow")
    return client


# callbacks
def on_connect(client, userdata, flags, rc):
    mqttLogger.warning("connection result: "+ mqtt.connack_string(rc))


def on_disconnect(client, userdata, rc):
    if rc != 0:
        mqttLogger.warning("unexpected disconnection")


def on_message(client, userdata, message):
    if message.topic == "atom/flow":
        # lettura sensore flusso acqua
        global portata
        portata = str(message.payload.decode("utf-8"))
        mqttLogger.info("atom/flow: {}".format(portata))


def pub_msg(mqtt_client, msg):
    msg_info = mqtt_client.publish("atom/water", msg)
    # check
    if msg_info.rc == mqtt.MQTT_ERR_SUCCESS:
        # attendiamo l'effettiva pubblicazione del messaggio
        msg_info.wait_for_publish()  # qui si blocca fino alla pubblicazione

        # logging
        if msg_info.is_published():
            mqttLogger.info("msg: {} >>> pub ok".format(msg))
        else:
            mqttLogger.warning("msg: {} >>> pub error".format(msg))

        return msg_info.is_published
    else:
        # in caso di errore generico
        mqttLogger.warning("msg: {} >>> pub error".format(msg))
        return False


########################################################################################################################
def main_loop(_client, _rubinetto, _programma):
    update_id = str()

    while True:
        # mqtt start update
        _client.loop_start()

        # monitoraggio portata rubinetto
        check_portata(_rubinetto)
        # gestione programma irrigazione
        _rubinetto, _programma = gestione_programma(_rubinetto, _programma, _client)
        # telegram bot update
        update_dict, update_id = update_bot(update_id)
        # elabora risposta
        if update_dict:
            # ci hanno inviato qualcosa tramite il bot
            _rubinetto, _programma = elabora_update(update_dict, _rubinetto, _programma, _client)

        # mqtt stop update
        _client.loop_stop()


########################################################################################################################
# main
if __name__ == "__main__":
    # init
    rubinetto, portata = init_rubinetto()
    programma = init_programma()
    client = crea_client(CLIENT_NAME, {"con": on_connect, "dis": on_disconnect, "msg": on_message}, BROKER_IP)

    # loop infinito
    main_loop(client, rubinetto, programma)
