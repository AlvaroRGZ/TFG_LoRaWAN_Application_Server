#!/bin/bash

# Autor: Álvaro Rodríguez Gómez

# Script para arrancar las aplicaciones necesarias para el
# funcionamiento de la aplicación

##### Constantes

TITLE="Runs the web application for accesing network data"

RIGHT_NOW=$(date +"%x %r%Z")
TIME_STAMP="Actualizada el $RIGHT_NOW por $USER"
RUN="[$TEXT_GREEN RUN $TEXT_RESET ] "

##### Estilos

TEXT_BOLD=$(tput bold)

TEXT_ULINE=$(tput sgr 0 1)

TEXT_GREEN=$(tput setaf 2)
TEXT_RESET=$(tput sgr0)

##### Funciones

# Ejecuta la pagina web de acceso a los datos
run_app() {
  cd /home/pi/TFG_LoRaWAN_Application_Server/
  source venv/bin/activate $ 
  # export FLASK_APP=app.py
  flask run --host 0.0.0.0 --port 8081
  echo "$RUN app.py"
}

mostrar_programa() {
  echo $TEXT_GREEN$TITLE$TEXT_RESET
  $(run_app)
}

$(mostrar_programa)
