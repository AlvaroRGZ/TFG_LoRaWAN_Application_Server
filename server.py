import os
import sys
import psycopg2
import paho.mqtt.client as mqtt
import time
import json
import datetime;
import requests;
import decimal

# Minimum message size for uplink
UPLINK_MESSAGE_SIZE = 7

# Data base connection
bbdd_host = 'localhost'
def get_db_connection():
  conn = psycopg2.connect(host='localhost',
        database = 'app',
        user = 'admin',password = 'passwd',
        port=5432)
  return conn

def on_message(client, userdata, message):
  """
  Define the function for the callback
  """
  message = str(message.payload.decode("utf-8"))
  msg = json.loads(message)

  if (len(msg) > UPLINK_MESSAGE_SIZE):
    look_for_new_gateways(msg)

    eui = msg["devEUI"]
    if search_eui(eui) == None:
      register_device(eui, msg["deviceName"],
                      msg["rxInfo"][0]["location"]["latitude"],
                      msg["rxInfo"][0]["location"]["longitude"],
                      msg["rxInfo"][0]["location"]["altitude"])
    else:
      save_data(msg)
      check_limits(msg)

def search_eui(eui):
  """
  Search a device in the database with that eui
  """
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
  """
  Registers a device with the providen information
  """
  conn = get_db_connection()
  cur = conn.cursor()

  cur.execute('INSERT INTO device '
              '(eui, name, latitude, longitude, altitude) VALUES '
              "('{}','{}', {}, {}, {})".format(eui, name, latitude, longitude, altitude))
  conn.commit()
  cur.close()
  conn.close()
  print("")
  print("[OK] Registered new device. EUI: {}".format(eui))

def save_data(msg):
  """
  Saves an uplink in the database
  """
  # Extract message data
  eui = msg["devEUI"]
  timestamp = datetime.datetime.now()
  frame_counter = 0 # msg["fCnt"], now deprecated
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
  print("[OK] Registered new uplink. EUI: {}".format(eui))

def look_for_new_gateways(msg):
  """
  Looks for new gateways in the uplink gateways info.
  If they are not in the database, registers it and 
  the relation between it and the device
  """
  conn = get_db_connection()
  cur = conn.cursor()
    
  for gateway in msg["rxInfo"]:
    cur.execute('SELECT name FROM gateway '
                "WHERE eui = \'{}\'".format(gateway["gatewayID"]))
    
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
      
      print("\n[OK] New gateway. EUI: {}".format(eui))

    # Link the device with the gateway if they´re not
    cur.execute('SELECT gat_eui FROM gateway_range ' 
                "WHERE gat_eui = \'{}\' AND dev_eui = \'{}\';".format(gateway["gatewayID"],
                                                                  msg["devEUI"]))
    if (len(cur.fetchall()) == 0):
      cur.execute('INSERT INTO gateway_range '
                  '(gat_eui, dev_eui) VALUES '
                  "('{}','{}')".format(gateway["gatewayID"], msg["devEUI"]))
  conn.commit()
  cur.close()
  conn.close()

def check_limits(msg):
  """
  Checks if there are limits defined for any parameter in uplink object.
  If there are and they are crossed, saves the alert and notify it by telegram 
  """
  conn = get_db_connection()
  cur = conn.cursor()

  limits = get_device_limits(msg["devEUI"])

  # Check for every parameter in uplink object if there is a limit defined for it
  for param, value in msg["object"].items():
    for limit in limits:
      if limit["parameter"] == param:
        # Check the conditions and if necessary register the alert and
        # build the message in markdown to notify it by telegram
        if (decimal.Decimal(value) < limit["min"]):
          desc = 'Valor del parámetro {} = {} inferior al minimo {}'.format(param, value, limit["min"])
          cur.execute('INSERT INTO alerts '
                      '(eui, descrip, param, value, date) VALUES '
                      "('{}','{}', '{}', {}, '{}');".format(msg["devEUI"], desc, param, value, datetime.datetime.now()))
          body = "Alert {} at {}".format(msg["deviceName"], datetime.datetime.now().strftime('%d de %B de %Y a las %H:%M:%S'))
          body += "\nRecibed value {} = {} exceeds min = {}".format(param, value, limit["min"])
          send_alert(body)
        if (decimal.Decimal(value) > limit["max"]):
          desc = 'Valor del parámetro {} = {} superior al maximo {}'.format(param, value, limit["max"])
          cur.execute('INSERT INTO alerts '
                      '(eui, descrip, param, value, date) VALUES '
                      "('{}','{}', '{}', {}, '{}');".format(msg["devEUI"], desc, param, value, datetime.datetime.now()))
          body = "Alert {} at {}".format(msg["deviceName"], datetime.datetime.now().strftime('%d de %B de %Y a las %H:%M:%S'))
          body += "\nRecibed value {} = {} exceeds max = {}".format(param, value, limit["max"])
          send_alert(body)

  conn.commit()
  cur.close()
  conn.close()

def get_device_limits(eui):
  """
  Get the device limits in a list of fixed JSON objects with the required information
  """
  conn = get_db_connection()
  cur = conn.cursor()
  
  cur.execute('SELECT parameter, min, max FROM device_limits '
              "WHERE eui = '{}'".format(eui))
  lim = cur.fetchall()

  limits = []
  if (len(lim) > 0):
    for l in lim:
      limits.append({
        "parameter": l[0],
        "min": decimal.Decimal(l[1]),
        "max": decimal.Decimal(l[2]),
      })

  cur.close()
  conn.close()
  return limits

def send_alert(msg):
  """
  Sends the Markdown formated message by telegram
  """
  bot_token = open(".telegram_bot_token").read()
  bot_chatID = '623684150'
  send_text =  'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id='
  send_text += bot_chatID + '&parse_mode=Markdown&text=' + msg
  requests.get(send_text)

# -----------------------------------------------------
# -------------------- Main script --------------------
# -----------------------------------------------------

gateway_host = "localhost"
# Build MQTT Broker' client
client = mqtt.Client("1")
client.on_message=on_message
client.connect(gateway_host)
client.subscribe("application/2/#")

# Listen indefinitely waiting for an interruption
client.loop_start()

while True:
  print("Listening for data ", end= "")
  sys.stdout.flush()
  for i in range(10):
    time.sleep(1)
    print(". ", end= "")
    sys.stdout.flush()
  time.sleep(1)
  print("")