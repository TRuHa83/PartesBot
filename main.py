from schedule import every, run_pending, clear
from telebot import TeleBot

from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from time import sleep

import threading as th
import logging as log
import archive
import send
import json
import sys
import os

# folders
work_folder = os.path.abspath(os.path.dirname(sys.argv[0]))
config_folder = os.path.join(os.path.dirname(work_folder), 'Config')
data_folder = os.path.join(os.path.dirname(work_folder), 'Documents')


# Logging config
def configure_logging():
    log.basicConfig(
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%d-%m-%Y %H:%M:%S',
        level=log.INFO,
        handlers=[
            log.StreamHandler()
        ]
    )


# Load logging config
configure_logging()

try:
    # TelegramBot Data
    TOKEN = os.getenv('TOKEN')
    AUTHORIZED_CHAT = int(os.getenv('CHATID'))

    bot = TeleBot(TOKEN)

except Exception as e:
    log.error(str(e))
    sys.exit(1)

# Globals
RUN = 1
WAIT = 0
STOP = 2
STATE = {}
CONFIG = {}
TIMES = {}
FILENAME = None

STATE['PROGRAM'] = STOP
STATE['CURRENT'] = None
STATE['REGISTRY'] = None

# Diccionario para almacenar el ultimo ID de mensaje del bot y user
message_ids = {
    'last_bot_message': None,
    'last_user_message': None
}

# Diccionario para almacenar los registros del dia
daily_registry = []


def load_config():
    global CONFIG

    # Lee el archivo config.json
    with open(f'{config_folder}/config.json') as f:
        CONFIG = json.load(f)


def get_list_time(entry_time, exit_time):
    hours, minutes = map(int, entry_time.split(':'))
    time_start = hours * 60 + minutes

    hours, minutes = map(int, exit_time.split(':'))
    time_end = hours * 60 + minutes

    return list(range(time_start, time_end + 1, 15))


# Manejador para asegurarse de que solo el usuario autorizado pueda interactuar
def authorized_handler(func):
    def wrapper(message):
        if message.chat.id == AUTHORIZED_CHAT:
            func(message)

        else:
            bot.send_message(message.chat.id, "No estás autorizado para usar este bot.")

    return wrapper


# Función para establecer el estado del bot
def set_state(VARIABLE, state, value):
    global STATE, CONFIG, TIMES
    VARIABLE[state] = value


# Contructor de menu
def make_menu(state):
    key_buttons = ReplyKeyboardMarkup(resize_keyboard=True)

    buttons = []
    for button in state:
        buttons.append(KeyboardButton(button))

    if len(buttons) % 2 == 0:
        for i in range(0, len(buttons), 2):
            key_buttons.row(buttons[i], buttons[i + 1])

    elif len(buttons) % 3 == 0:
        for i in range(0, len(buttons), 3):
            key_buttons.row(buttons[i], buttons[i + 1], buttons[i + 2])

    elif len(buttons) % 5 == 0:
        for i in range(0, len(buttons), 5):
            key_buttons.row(buttons[i], buttons[i + 1])
            key_buttons.row(buttons[i + 2], buttons[i + 3])
            key_buttons.row(buttons[i + 4])

    else:
        for button in buttons:
            key_buttons.add(button)

    return key_buttons


# Borra los ultimos mensajes
def delete_last_message():
    try:
        if message_ids['last_bot_message'] is not None:
            bot.delete_message(AUTHORIZED_CHAT, message_ids['last_bot_message'])
            message_ids['last_bot_message'] = None

        if message_ids['last_user_message'] is not None:
            bot.delete_message(AUTHORIZED_CHAT, message_ids['last_user_message'])
            message_ids['last_user_message'] = None

    except Exception as e:
        log.error(str(e))


# Comando /start para inicializar el bot
@bot.message_handler(commands=['start'])
@authorized_handler
def start(message):
    set_state(STATE, 'CURRENT', None, )
    set_state(TIMES, 'ENTRY', CONFIG['ENTRY'])
    set_state(TIMES, 'EXIT', CONFIG['EXIT'])
    set_state(TIMES, 'LIST', get_list_time(CONFIG['ENTRY'], CONFIG['EXIT']))

    buttons = ['Registro', 'Archivos', 'Ajustes', 'Salir']
    key_buttons = make_menu(buttons)

    if CONFIG['BOT']:
        set_state(STATE, 'PROGRAM', RUN, )
        set_state(CONFIG, 'BOT', False, )
        bot.send_message(AUTHORIZED_CHAT, 'Bot iniciado')
        log.info('Bot iniciado')

    bot.send_message(AUTHORIZED_CHAT, "Seleccione una opción.", reply_markup=key_buttons)


# Comando /stop para detener cualquier proceso
@bot.message_handler(commands=['stop'])
@authorized_handler
def stop(message):
    set_state(STATE, 'CURRENT', None, )
    key_buttons = make_menu(['Empezar', 'Ajustes'])

    if not CONFIG['BOT']:
        set_state(STATE, 'PROGRAM', STOP, )
        set_state(CONFIG, 'BOT', True, )
        bot.send_message(AUTHORIZED_CHAT, 'Bot detenido', reply_markup=ReplyKeyboardRemove())
        log.warning('Bot detenido')

        bot.send_message(AUTHORIZED_CHAT, 'Pulse para empezar.', reply_markup=key_buttons)


# Manejador de mensajes cuando el estado es NONE
@bot.message_handler(func=lambda message: STATE['CURRENT'] is None)
@authorized_handler
def handle_default(message):
    accion = message.text

    if accion == "Empezar":
        # Lógica para iniciar el bot
        bot.send_message(AUTHORIZED_CHAT, "Bienvenido.",
                         reply_markup=ReplyKeyboardRemove())

        set_state(CONFIG, 'BOT', True, )
        start(message)

    elif accion == "Registro":
        if STATE['REGISTRY'] == 'saved':
            bot.send_message(AUTHORIZED_CHAT, f"Registro diario guardado. Comprobar en archivo")
            log.info('Registro guardando, no se realiza accion')

            start(message)

        elif STATE['REGISTRY'] != 'complete':
            # Lógica para hacer registro diario
            bot.send_message(AUTHORIZED_CHAT, f"Iniciando registro diario.",
                             reply_markup=ReplyKeyboardRemove())

            log.info('Iniciando registro diario')
            set_state(STATE, 'CURRENT', 'daily_registry', )

            handle_daily_registry(message)

        elif STATE['REGISTRY'] == 'complete':
            # Lógica para comprobar diario
            bot.send_message(AUTHORIZED_CHAT, f"Registro diario completo.")
            log.info('Comprobar registro')
            set_state(STATE, 'CURRENT', 'check_registry', )

            handle_check_registry(message)

    elif accion == "Archivos":
        # Lógica para hacer gestionar los archivos
        bot.send_message(AUTHORIZED_CHAT, f"Menú de archivos en construccion.",
                         reply_markup=ReplyKeyboardRemove())

        log.info('Gestion de archivos')
        start(message)

    elif accion == "Ajustes":
        set_state(STATE, 'CURRENT', 'setting')
        markup = InlineKeyboardMarkup()

        for value in CONFIG.keys():
            text = f'{value}: {CONFIG[value]}'
            btn_callback = InlineKeyboardButton(text=text, callback_data=value)
            markup.add(btn_callback)

        # Enviar mensaje con el teclado inline
        bot.send_message(message.chat.id, "*CONFIGURACION*", parse_mode='MarkdownV2', reply_markup=markup)

        key_buttons = make_menu(['Volver'])
        bot.send_message(message.chat.id, "Pulse para editar el valor", reply_markup=key_buttons)

        log.info('Ajustes del BOT')

    elif accion == "Salir":
        # Lógica para detener el bot
        log.info('Salir')
        set_state(CONFIG, 'BOT', False, )

        stop(message)

    elif accion == "Enviar":
        try:
            send.file(FILENAME)

        except Exception as e:
            log.error(str(e))
            bot.send_message(AUTHORIZED_CHAT, 'Error al enviar el fichero.')
            bot.send_message(AUTHORIZED_CHAT, 'Compruebe configuracion.')

        else:
            log.info('eMail enviado')
            bot.send_message(AUTHORIZED_CHAT, 'Fichero enviado correctamente.')

        finally:
            start(message)

    else:
        message_ids['last_user_message'] = message.message_id
        delete_last_message()

        bot.send_message(AUTHORIZED_CHAT, "Opción no válida.")
        log.warning('Opción no válida')

        start(message)


@bot.message_handler(func=lambda message: STATE['CURRENT'] == 'setting')
@authorized_handler
def handle_setting(message):
    accion = message.text

    if accion == "Volver":
        set_state(STATE, 'CURRENT', None)

        log.info('Volver')

        if CONFIG['BOT']:
            start(message)

        else:
            stop(message)


@bot.callback_query_handler(func=lambda call: True and STATE['CURRENT'] == 'setting')
def callback_query(call):
    log.info(f'Setting: {call.data}')


# Manejador de mensajes para el estado de registro diario
@bot.message_handler(func=lambda message: STATE['CURRENT'] == "daily_registry")
@authorized_handler
def handle_daily_registry(message):
    global daily_registry

    accion = message.text

    if accion == 'Festivo' or accion == 'Vacaciones':
        set_state(STATE, 'REGISTRY', 'complete', )
        log.info(accion)

        daily_registry.append({
            'site': accion,
            'entry': '',
            'exit': ''
        })

    elif accion == 'Cancelar':
        log.info('Cancelar')

        set_state(STATE, 'CURRENT', None, )
        set_state(STATE, 'REGISTRY', accion, )
        start(message)

    if STATE['REGISTRY'] is None:
        buttons = ["Festivo", "Vacaciones", "Cancelar"]
        key_buttons = make_menu(buttons)

        bot.send_message(AUTHORIZED_CHAT, f"¿Donde ha estado hoy?", reply_markup=key_buttons)
        set_state(STATE, 'REGISTRY', 'site', )

    elif STATE['REGISTRY'] == 'site':
        log.info(f'Lugar: {message.text}')
        daily_registry.append({'site': message.text,
                               'entry': 450,
                               'exit': None})

        time = daily_registry[-1]['entry']

        if len(daily_registry) > 1:
            time = daily_registry[-2]['exit']
            daily_registry[-1]['entry'] = time

        bot.send_message(AUTHORIZED_CHAT, f"Hora de entrada {archive.get_time(time)}")

        hour_selector(message)

    elif STATE['REGISTRY'] == 'hour':
        delete_last_message()

        log.info(f'Hora salida: {message.text}')
        daily_registry[-1]['exit'] = archive.get_time(message.text)

        if message.text == TIMES['EXIT']:
            set_state(STATE, 'REGISTRY', 'complete', )
            handle_daily_registry(message)

        else:
            bot.send_message(AUTHORIZED_CHAT, f"¿Otro sitio?")
            set_state(STATE, 'REGISTRY', 'site', )

    elif STATE['REGISTRY'] == 'complete':
        bot.send_message(AUTHORIZED_CHAT, f"Registro completado")
        log.info('Registro completado')

        set_state(STATE, 'CURRENT', 'check_registry', )
        message.text = 'Registro'
        handle_check_registry(message)

    else:
        set_state(STATE, 'REGISTRY', None, )


# Manejador de mensajes para el estado de comprobador registro
@bot.message_handler(func=lambda message: STATE['CURRENT'] == "check_registry")
@authorized_handler
def handle_check_registry(message):
    global daily_registry

    accion = message.text

    if accion == "Registro":
        buttons = ['Ver', 'Cambiar', 'Borrar', 'Cancelar', 'Guardar']
        key_buttons = make_menu(buttons)

        bot.send_message(AUTHORIZED_CHAT, f"¿Que desea hacer?", reply_markup=key_buttons)

    elif accion == "Ver":
        log.info('Ver registro')

        for reg in daily_registry:
            t_entry = archive.get_time(reg['entry'])
            t_exit = archive.get_time(reg['exit'])
            text = f"{reg['site']} [{t_entry} a {t_exit}]"
            bot.send_message(AUTHORIZED_CHAT, text)

    elif accion == "Cambiar":
        daily_registry = []
        set_state(STATE, 'CURRENT', 'daily_registry', )
        set_state(STATE, 'REGISTRY', None, )

        log.info('Cambiar')

        handle_daily_registry(message)

    elif accion == "Borrar":
        daily_registry = []

        set_state(STATE, 'CURRENT', None, )
        set_state(STATE, 'REGISTRY', None, )

        bot.send_message(AUTHORIZED_CHAT, f"Registro diario borrado")
        log.info('Borrar')

        start(message)

    elif accion == "Cancelar":
        log.info('Cancelar')

        set_state(STATE, 'CURRENT', None, )
        start(message)

    elif accion == "Guardar":
        log.info('Guardar datos')

        data = {
            'name': CONFIG['NAME'],
            'data_folder': data_folder,
            'daily_registry': daily_registry
        }

        try:
            archive.save(data)

        except Exception as error:
            bot.send_message(AUTHORIZED_CHAT, 'Error al guardar datos, compruebe el log')
            log.error(str(error))

        else:
            bot.send_message(AUTHORIZED_CHAT, 'Datos guardados correctamente.')
            log.info('Datos guardados correctamente')

        set_state(STATE, 'CURRENT', None, )
        set_state(STATE, 'REGISTRY', 'saved', )
        start(message)


@bot.message_handler(func=lambda message: STATE['CURRENT'] == "hour_selector")
@authorized_handler
def hour_selector(message):
    delete_last_message()

    bot.send_message(AUTHORIZED_CHAT, f"¿Hora de salida?", reply_markup=ReplyKeyboardRemove())

    threshold_min = daily_registry[-1]['entry']
    time_list = TIMES['LIST']

    filtered_list = [number for number in time_list if number > threshold_min]
    hours_set = set(hour // 60 for hour in filtered_list)
    key_buttons = make_menu(sorted(hours_set))

    sent_message = bot.send_message(AUTHORIZED_CHAT, "Seleccione la hora", reply_markup=key_buttons)
    message_ids['last_bot_message'] = sent_message.message_id

    set_state(STATE, 'CURRENT', 'minute_selector', )


@bot.message_handler(func=lambda message: STATE['CURRENT'] == "minute_selector")
@authorized_handler
def minute_selector(message):
    message_ids['last_user_message'] = message.message_id
    delete_last_message()

    hour = int(message.text)
    threshold_min = daily_registry[-1]['entry']
    threshold_max = archive.get_time(TIMES['EXIT'])

    list_min = []
    number = [0, 15, 30, 45]
    for n in number:
        list_min.append(hour * 60 + n)

    minutes = [num for num in list_min if threshold_min < num <= threshold_max]

    list_min.clear()
    for m in minutes:
        list_min.append(archive.get_time(m))

    key_buttons = make_menu(list_min)

    sent_message = bot.send_message(AUTHORIZED_CHAT, "Seleccione los minutos", reply_markup=key_buttons)
    message_ids['last_bot_message'] = sent_message.message_id

    set_state(STATE, 'CURRENT', 'daily_registry', )
    set_state(STATE, 'REGISTRY', 'hour', )


def end_day():
    global daily_registry
    while STATE['REGISTRY'] != 'saved':
        daily_registration()
        sleep(60)

    bot.send_message(AUTHORIZED_CHAT, "Dia completado.")
    set_state(STATE, 'REGISTRY', None, )

    daily_registry.clear()


def end_work_week():
    global FILENAME
    end_day()

    name = CONFIG['NAME'].split(" ")
    FILENAME = archive.get_filename(name)

    if send.get_config():
        key_buttons = make_menu(['Enviar'])
        bot.send_document(AUTHORIZED_CHAT, document=open(f"{data_folder}/{FILENAME}", 'rb'), reply_markup=key_buttons)

        log.info(f'Se ha enviado el archivo: {FILENAME}')

    else:
        message = bot.send_message(AUTHORIZED_CHAT, 'Correo electronico no configurado')
        start(message)


# Función que se ejecutará automáticamente cada día a la hora especificada
def daily_registration():
    if STATE['REGISTRY'] is None:
        set_state(STATE, 'CURRENT', 'daily_registry', )
        message = bot.send_message(AUTHORIZED_CHAT, "Es hora de tu registro diario.")
        log.info('Registro automatico')

        message.text = "Registro"
        handle_default(message)

    elif STATE['REGISTRY'] == 'complete':
        set_state(STATE, 'CURRENT', 'check_registry', )
        message = bot.send_message(AUTHORIZED_CHAT, "Registo completado, guardando...")
        log.info('Registro completo, guardando')

        message.text = "Guardar"
        handle_check_registry(message)

    elif STATE['REGISTRY'] == 'saved':
        bot.send_message(AUTHORIZED_CHAT, "Registo completado y guardando, no se realizara ninguna accion.")
        log.info('Registro guardando, no se realizara ninguna accion')

    else:
        set_state(STATE, 'REGISTRY', None, )
        daily_registration()


def schedule_tasks():
    registration = CONFIG['REGISTRATION']
    reset = CONFIG['RESET']

    # Lunes
    every().monday.at(registration).do(daily_registration)
    every().monday.at(reset).do(end_day)

    # Martes
    every().tuesday.at(registration).do(daily_registration)
    every().tuesday.at(reset).do(end_day)

    # Miercoles
    every().wednesday.at(registration).do(daily_registration)
    every().wednesday.at(reset).do(end_day)

    # Jueves
    every().thursday.at(registration).do(daily_registration)
    every().thursday.at(reset).do(end_day)

    # Viernes
    every().friday.at(registration).do(end_work_week)
    #every().friday.at(reset).do(end_day)


# Mantener el bot y las tareas de schedule en ejecución
def run_schedule():
    while STATE['PROGRAM'] == WAIT:
        run_pending()
        sleep(1)


def manage_schedule_thread():
    while control_thread:
        if STATE['PROGRAM'] == RUN:
            set_state(STATE, 'PROGRAM', WAIT, )
            log.info('Programador iniciado')

            clear()
            schedule_tasks()

            run_schedule()

        if STATE['PROGRAM'] == STOP:
            set_state(STATE, 'PROGRAM', WAIT, )
            log.info('Programador detenido')

            clear()

        sleep(1)


if __name__ == '__main__':
    control_thread = True
    thread = None

    try:
        load_config()

        log.info('Servicio inciado')

        sent_message = bot.send_message(AUTHORIZED_CHAT, 'Servicio iniciado',
                                        reply_markup=ReplyKeyboardRemove())

        thread = (th.Thread(target=manage_schedule_thread))
        thread.start()

        if not CONFIG['BOT']:
            stop(sent_message)

        else:
            start(sent_message)

        bot.infinity_polling()

    except Exception as e:
        log.error(str(e))

    finally:
        log.warning('Servicio detenido')

        control_thread = False

        if thread is not None and thread.is_alive():
            thread.join()

        sys.exit(1)

