# Usa la imagen base de Python optimizada
FROM python:3.12

# Establece las variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV TZ=Europe/Madrid

# Crea los directorios necesarios en el contenedor
RUN mkdir -p /PartesBot /Documents /Config

# Copia archivos necesarios al contenedor
COPY requirements.txt /PartesBot/
COPY intratime.py /PartesBot/
COPY archive.py /PartesBot/
COPY send.py /PartesBot/
COPY main.py /PartesBot/

# Copia los archivos de configuración predeterminados
COPY config.json /PartesBot/default_config.json
COPY email.json /PartesBot/default_email.json

# Copia el script de entrada
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Establece el directorio de trabajo
WORKDIR /PartesBot

# Instala las dependencias requeridas
RUN pip install --upgrade --no-cache-dir -r requirements.txt

# Usar el script de entrada
ENTRYPOINT ["/entrypoint.sh"]