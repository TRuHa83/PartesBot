#!/bin/bash

# Copiar archivos solo si no existen
if [ ! -f /Config/config.json ]; then
    cp /PartesBot/default_config.json /Config/config.json
fi

if [ ! -f /Config/email.json ]; then
    cp /PartesBot/default_email.json /Config/email.json
fi

# Iniciar la aplicación
exec python3 main.py
