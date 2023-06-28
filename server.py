import os
import sys
import psycopg2
import paho.mqtt.client as mqtt
import time
import json
import datetime;

# Definimos la cola en la que se almacenaran los datos recibidos
import queue as queue
q = queue.Queue()

# Configurar la conexion con la base de datos
bbdd_host = 'localhost'
def get_db_connection():
  conn = psycopg2.connect(host='localhost',
        database = 'app',
        user = 'admin',password = 'passwd',
        port=5432)
  return conn

# Definir la funcion para el callback
def on_message(client, userdata, message):
  #q.put(message)
  message = str(message.payload.decode("utf-8"))
  msg = json.loads(message)

  look_for_new_gateways(msg)

  eui = msg["devEUI"]
  if search_eui(eui) == None:
    register_device(eui, msg["deviceName"],
                    msg["rxInfo"][0]["location"]["latitude"],
                    msg["rxInfo"][0]["location"]["longitude"],
                    msg["rxInfo"][0]["location"]["altitude"])
  else:
    save_data(msg)

def search_eui(eui):
  conn = get_db_connection()
  cur = conn.cursor()

  cur.execute('SELECT name FROM device '
              "WHERE eui = '{}';".format(eui))
  dev_name = cur.fetchall()
  
  cur.close()
  conn.close()

  if len(dev_name) > 0:
    return dev_name[0]
  else:
    return None
  
def register_device(eui, name, latitude, longitude, altitude):
  conn = get_db_connection()
  cur = conn.cursor()

  cur.execute('INSERT INTO device '
              '(eui, name, latitude, longitude, altitude) VALUES '
              "('{}','{}', {}, {}, {})".format(eui, name, latitude, longitude, altitude))
  conn.commit()
  cur.close()
  conn.close()
  print("")
  print("[OK] Dispositivo nuevo registrado. EUI: {}".format(eui))

def save_data(msg):
  # Extract message data
  eui = msg["devEUI"]
  timestamp = datetime.datetime.now()
  frame_counter = 0#msg["fCnt"]
  obj = msg["object"]

  conn = get_db_connection()
  cur = conn.cursor()

  cur.execute('INSERT INTO data '
              '(eui, rec_date, frame_counter, obj) VALUES '
              "('{}','{}', {}, '{}')".format(eui, timestamp, frame_counter, json.dumps(obj)))
  conn.commit()
  cur.close()
  conn.close()
  print("")
  print("[OK] Registro nuevo registrado. EUI: {}".format(eui))

def look_for_new_gateways(msg):
  conn = get_db_connection()
  cur = conn.cursor()
  
  for gateway in msg["rxInfo"]:
    cur.execute('SELECT name FROM gateway '
                "WHERE eui = '{}'".format(gateway["gatewayID"]))
    
    if (len(cur.fetchall()) == 0):
      # Save gateway data
      eui = gateway["gatewayID"]
      nam = gateway["name"]
      lat = gateway["location"]["latitude"]
      lon = gateway["location"]["longitude"]
      alt = gateway["location"]["altitude"]

      cur.execute('INSERT INTO gateway '
                  '(eui, name, latitude, longitude, altitude) VALUES '
                  "('{}','{}', {}, '{}', '{}')".format(eui, nam, lat, lon, alt))
      conn.commit()
      print("\n[OK] New gateway. EUI: {}".format(eui))

  cur.close()
  conn.close()

gateway_host = "localhost"
# -------------------- Main script --------------------
# Establecemos el cliente del MQTT Broker
client = mqtt.Client("1")
client.on_message=on_message
client.connect(gateway_host)
client.subscribe("application/2/#")

client.loop_start()  #Se queda indefinidamente esperando a una interrupcin

while True:
  print("Listening for data ", end= "")
  sys.stdout.flush()
  for i in range(10):
    time.sleep(1)
    print(". ", end= "")
    sys.stdout.flush()
  time.sleep(1)
  print("")

#print (datetime.datetime.now())