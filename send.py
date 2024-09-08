import yagmail
import json
import sys
import os


# folders
work_folder = os.path.abspath(os.path.dirname(sys.argv[0]))
data_folder = os.path.join(os.path.dirname(work_folder), 'Documents')
config_folder = os.path.join(os.path.dirname(work_folder), 'Config')


def get_config():
    config_file = f'{config_folder}/email.json'

    # Si el archivo no existe, crearlo con valores por defecto
    if not os.path.isfile(config_file):
        config = {
            "smtp_server": "none",
            "smtp_port": "none",
            "email": "none",
            "password": "none",
            "send_to": "none"
        }
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)  # Usar json.dump para escribir el archivo

        return False

    # Leer configuración del archivo
    with open(config_file, 'r') as f:
        config = json.load(f)

    # Verificar si algún campo tiene el valor "none"
    if any(value == "none" for value in config.values()):
        return False

    return True


def file(filename):
    # Leer configuración desde el archivo JSON
    with open(f'{config_folder}/email.json', 'r') as f:
        config = json.load(f)

    # datos para el servidor de correo
    smtp_server = config.get("smtp_server")
    smtp_port = config.get("smtp_port")
    from_email = config.get("email")
    password = config.get("password")
    to_email = config.get("send_to")
    subject = "Partes de trabajo"
    body = "Correo enviado automaticamente."

    yag = yagmail.SMTP(host=smtp_server, port=smtp_port, user=from_email, password=password)

    # Enviar el correo con el archivo adjunto
    yag.send(
        to=to_email,
        subject=subject,
        contents=body,
        attachments=f'{data_folder}/{filename}'
    )

    print("Correo enviado con éxito")
