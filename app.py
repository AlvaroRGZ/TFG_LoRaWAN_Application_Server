import os
import sys

import psycopg2
from flask import Flask, render_template, request, url_for, redirect, flash
from flask_bootstrap import Bootstrap4
import json
import paho.mqtt.client as mqtt

# Para realizar las graficas
import pandas as pd
import decimal
import plotly
import plotly.express as px
import datetime

# Para mostrar mapas
import plotly.graph_objects as go

app = Flask(__name__)

bootstrap = Bootstrap4(app)

bbdd_host = 'localhost'
def get_db_connection():
  conn = psycopg2.connect(host='localhost',
                          database = 'app',
                          user = 'admin',password = 'passwd',
                          port=5432)
  return conn

def is_json(myjson):
  try:
    json.loads(myjson)
  except ValueError as e:
    return False
  return True

def get_object(vector, campo, valor):
  for obj in vector:
    if obj[campo] == valor:
      return obj
  return None

@app.route('/')
def index():
  
  conn = get_db_connection()
  cur = conn.cursor()

  cur.execute('SELECT eui, name, latitude, longitude, altitude FROM device;')
  devices = cur.fetchall()

  cur.execute('SELECT eui, name, latitude, longitude, altitude FROM gateway;')
  gateways = cur.fetchall()
  cur.close()
  conn.close()

  return render_template('index.html', devices_ = devices, gateways_ = gateways)

@app.route('/device/<dev>')
def device(dev):
  conn = get_db_connection()
  cur = conn.cursor()

  # Get device information
  cur.execute('SELECT * '
              'FROM device '
              'WHERE eui = \'{}\''.format(dev))
  dev_info = cur.fetchall()

  # Get device uplinks
  cur.execute('SELECT eui, rec_date, obj '
              'FROM data '
              "WHERE eui = \'{}\'".format(dev) + ' ORDER BY rec_date DESC;')
  dev_data = cur.fetchall()

  # Construct the obj json
  uplink_objs = []
  for uplink in dev_data:
    uplink_objs.append(uplink[2])

  print(dev_data)

  cur.close()
  conn.close()
  return render_template("device/device.html",
                         dev_info_ = dev_info,
                         dev_data_ = dev_data,
                         uplink_objs_ = uplink_objs)

@app.route('/gateway/<eui>')
def gateway(eui):
  conn = get_db_connection()
  cur = conn.cursor()

  # Get gateway information
  cur.execute('SELECT * '
              'FROM gateway '
              'WHERE eui = \'{}\''.format(eui))
  gat_info = cur.fetchall()

  # Get gateway' devices in range information
  cur.execute('SELECT device.name, data.rec_date '
              'FROM gateway_range CROSS JOIN data CROSS JOIN device '
              'WHERE gateway_range.dev_eui = data.eui AND data.eui = device.eui AND '
              'gat_eui = \'{}\' '
              'GROUP BY device.eui, data.rec_date '
              'HAVING data.rec_date >= ALL (SELECT rec_date '
              'FROM data '
              'WHERE eui = device.eui);'.format(eui))

  devs = cur.fetchall()

  cur.close()
  conn.close()
  return render_template("gateway/gateway.html",
                         gat_info_ = gat_info[0],
                         devs_ = devs)

# [Deprecated] Now the app registers the devices automatically
@app.route('/register_device', methods=('GET', 'POST'))
def register():
  if request.method == 'POST':
    conn = get_db_connection()
    cur = conn.cursor()

    # Check if device already exits, creates a new one if not
    cur.execute('SELECT * '
                'FROM device '
                'WHERE eui = \'{}\''.format(request["eui"]))
    device = cur.fetchall()
    if device != None:
      return render_template("error.html", errorMessage = "Device already exits")
    else:
      cur.execute('INSERT INTO device VALUES ('
                  '\'{}\',\'{}\',\'{}\',\'{}\',\'{}\');'.format(request["eui"],
                                                                request["name"],
                                                                request["latitude"],
                                                                request["longitude"],
                                                                request["altitude"]))
    cur.close()
    conn.close()
    return render_template("device/register_device.html",
                            errorMessage = "Registered new device named: {}".format(request["name"]))
  elif request.method == 'GET':
    conn = get_db_connection()
    cur = conn.cursor()

    # Get device information
    cur.execute('SELECT name FROM gateway;')
    gateway_names = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("device/register_device.html", gateways = gateway_names)
  else:
    return render_template("error.html", errorMessage="Error registrando dispositivo")

# Define a custom function to serialize datetime objects
def serialize_datetime(obj):
  if isinstance(obj, datetime.datetime):
    return obj.isoformat()
  raise TypeError("Type not serializable")

# Show the graph screen for that device and more information
@app.route('/device/<dev>/graph', methods=['GET', 'POST'])
def devicegraph(dev):
  if request.method == 'POST':
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    conn = get_db_connection()
    cur = conn.cursor()

    # Check if exists a previous range
    cur.execute('SELECT COUNT(*) FROM web_preferences WHERE eui = %s', (dev,))
    existing_records = cur.fetchone()[0]

    if existing_records > 0:
        # Update actual range
        cur.execute('UPDATE web_preferences SET begin_time = %s, end_time = %s WHERE eui = %s', (start_date, end_date, dev))
    else:
        # Upload a new range
        cur.execute('INSERT INTO web_preferences (eui, begin_time, end_time) VALUES (%s, %s, %s)', (dev, start_date, end_date))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('devicegraph', dev=dev))

  conn = get_db_connection()
  cur = conn.cursor()

  # Get time range
  cur.execute('SELECT begin_time, end_time '
              'FROM web_preferences '
              "WHERE eui = \'{}\'".format(dev))
  dates = cur.fetchall()
  data = []
  if len(dates) > 0:
    # Get registered data from device in that time range
    cur.execute('SELECT rec_date, obj '
                'FROM data '
                'WHERE eui = \'{}\' AND '
                'rec_date BETWEEN \'{}\' AND \'{}\'  '
                'ORDER BY rec_date DESC;'.format(dev,
                                                dates[0][0],
                                                dates[0][1]))
    data = cur.fetchall()
  else:
    # Get all the data
    cur.execute('SELECT rec_date, obj '
                'FROM data '
                'WHERE eui = \'{}\' '
                'ORDER BY rec_date DESC;'.format(dev))
    data = cur.fetchall()

  # Get last device uplink
  cur.execute('SELECT rec_date, obj '
              'FROM data '
              'WHERE eui = \'{}\' '
              'ORDER BY rec_date DESC LIMIT 1;'.format(dev))
  last_uplink = cur.fetchall()

  # Get device information
  cur.execute('SELECT * '
              'FROM device '
              "WHERE eui = \'{}\'".format(dev))
  device_data = cur.fetchall()

  dev_data = {
    "eui": device_data[0][0],
    "name": device_data[0][1],
    "latitude": device_data[0][2],
    "longitude": device_data[0][3],
    "altitude": device_data[0][4],
    "description": device_data[0][5]
  }
  uplink = []
  if (len(last_uplink) > 0):
    uplink = last_uplink[0]
    
  if (len(data) > 0):
    # format the date properly
    fecha_formateada = data[0][0].strftime('%d de %B de %Y, %H:%M:%S')

    ## Convert Query Result in dataframe
    dump = json.dumps(data, default=serialize_datetime)
    dict1 = json.loads(dump)
    yData = []

    register = dict(dict1[0][1])
    for key, value in register.items():
        yData.append(key)
    dict2 = []
    for r in dict1:
        r[1]["rec_date"] = pd.to_datetime(r[0])  # Convertir la fecha a Timestamp
        dict2.append(r[1])

    normalized = pd.json_normalize(dict2)
    df = pd.DataFrame(normalized)

    graphs = []
    # Build every graph
    for variable in yData:
      df[variable] = df[variable].astype(float)
      fig = px.line(df, x = 'rec_date', y = variable, color_discrete_sequence=px.colors.qualitative.Plotly, markers=True)
      # Show the limits if they exists
      cur.execute('SELECT min, max '
                  'FROM device_limits '
                  "WHERE eui = \'{}\' AND parameter = \'{}\'".format(dev, variable))
      min_max = cur.fetchall()
      if (min_max and min_max[0][0] is not None):
        fig.add_shape(type='line',
                      x0=df['rec_date'].min(),
                      x1=df['rec_date'].max(),
                      y0=min_max[0][0],
                      y1=min_max[0][0],
                      line=dict(color='red', dash='dash'),
                      name='min')
      if (min_max and min_max[0][1] is not None):
        fig.add_shape(type='line',
                      x0=df['rec_date'].min(),
                      x1=df['rec_date'].max(),
                      y0=min_max[0][1],
                      y1=min_max[0][1],
                      line=dict(color='green', dash='dash'),
                      name='max')

      fig.update_layout(showlegend=True)
      graphs.append(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))

    description = "Received data from device with EUI: {}".format(dev)

    cur.close()
    conn.close()
    
    return render_template('device/graph.html', graphJSON=graphs,
                          description=description,
                          uplink_ = uplink, dev_info_ = dev_data,
                          headers_=yData, fecha_formateada_ = fecha_formateada)
  else:

    cur.close()
    conn.close()
    aviso = "No data received in that period of time"
    return render_template('device/graph.html', graphJSON=[],
                          aviso_ = aviso,
                          uplink_ = uplink, dev_info_ = dev_data)

@app.route('/modify/device/<eui>', methods=('GET', 'POST'))
def modify_device(eui):
  if request.method == 'POST':
    conn = get_db_connection()
    cur = conn.cursor()

    # Check if device already exits, creates a new one if not
    cur.execute('UPDATE device SET '
                'description = \'{}\', '
                'latitude = \'{}\', '
                'longitude = \'{}\', '
                'altitude = \'{}\' '
                'WHERE eui = \'{}\''.format(request.form.get("new_desc"),
                                            request.form.get("new_latitude"),
                                            request.form.get("new_longitude"),
                                            request.form.get("new_altitude"),
                                            eui))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('modify_device', eui=eui))
  elif request.method == 'GET':
    conn = get_db_connection()
    cur = conn.cursor()

    # Get device information
    cur.execute('SELECT * FROM device WHERE eui=\'{}\';'.format(eui))
    device = cur.fetchall()
    # From tuple to struct
    dev = {
      "eui": device[0][0],
      "name": device[0][1],
      "latitude": device[0][2],
      "longitude": device[0][3],
      "altitude": device[0][4],
      "description": device[0][5]
    }

    res = ""
    cur.close()
    conn.close()
    return render_template("device/modify_device.html", dev_ = dev, res_=res)
  else:
    return render_template("error.html", errorMessage="Error registrando dispositivo")

@app.route('/modify/gateway/<eui>', methods=('GET', 'POST'))
def modify_gateway(eui):
  if request.method == 'POST':
    conn = get_db_connection()
    cur = conn.cursor()

    # Check if device already exits, creates a new one if not
    cur.execute('UPDATE gateway SET '
                'description = \'{}\', '
                'latitude = \'{}\', '
                'longitude = \'{}\', '
                'altitude = \'{}\' '
                'WHERE eui = \'{}\''.format(request.form.get("new_desc"),
                                            request.form.get("new_latitude"),
                                            request.form.get("new_longitude"),
                                            request.form.get("new_altitude"),
                                            eui))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('modify_gateway', eui = eui))
  elif request.method == 'GET':
    conn = get_db_connection()
    cur = conn.cursor()

    # Get gateway information
    cur.execute('SELECT * FROM gateway WHERE eui=\'{}\';'.format(eui))
    gateway = cur.fetchall()
    # From tuple to struct
    gat = {
      "eui": gateway[0][0],
      "name": gateway[0][1],
      "latitude": gateway[0][2],
      "longitude": gateway[0][3],
      "altitude": gateway[0][4],
      "description": gateway[0][5]
    }

    print(gat)
    res = ""
    cur.close()
    conn.close()
    return render_template("gateway/modify_gateway.html", gat_ = gat, res_=res)
  else:
    return render_template("error.html", errorMessage="Error registrando dispositivo")

@app.route('/limits/<eui>', methods=('GET', 'POST'))
def limits(eui):
  if request.method == 'GET':
    conn = get_db_connection()
    cur = conn.cursor()

    # Get device information
    cur.execute('SELECT name FROM device WHERE eui=\'{}\';'.format(eui))
    name = cur.fetchall()

    # Get limits information
    cur.execute('SELECT parameter, min, max FROM device_limits WHERE eui=\'{}\';'.format(eui))
    dev_limits = cur.fetchall()

    # Get device atributes
    cur.execute('SELECT obj FROM data WHERE eui=\'{}\';'.format(eui))
    parameters = cur.fetchall()

    ## Convert Query Result in dataframe
    dump = json.dumps(parameters[0], default=serialize_datetime)
    dict1 = json.loads(dump)

    parameter_names = []
    for key, value in dict1[0].items():
      parameter_names.append(key)
    # From tuple to struct
    limits = []
    print(parameter_names)
    for limit in dev_limits:
      l = {
        "parameter": limit[0],
        "min": limit[1],
        "max": limit[2]
      }
      limits.append(l)

    print(limits)
    cur.close()
    conn.close()
    return render_template("device/limits.html", limits_ = limits, parameters_ = parameter_names,
                            eui_ = eui, name_ = name[0][0], get_object = get_object)
  
  elif request.method == 'POST':
    conn = get_db_connection()
    cur = conn.cursor()

    # Get device parameters
    cur.execute('SELECT obj FROM data WHERE eui=\'{}\';'.format(eui))
    parameters = cur.fetchall()

    # Convert Query Result to dataframe
    dump = json.dumps(parameters[0], default=serialize_datetime)
    dict1 = json.loads(dump)

    parameter_names = []
    for key, value in dict1[0].items():
      parameter_names.append(key)

    form_items = list(request.form.items())
    for p in parameter_names:
      name = request.form.get(f"{p}_name")
      mind = request.form.get(f"{p}_new_min")
      maxd = request.form.get(f"{p}_new_max")

      if mind or maxd:
        # Check if the record already exists
        cur.execute("SELECT COUNT(*) FROM device_limits WHERE eui = %s AND parameter = %s;", (eui, p))
        count = cur.fetchone()[0]

        if count > 0:
          # Update the existing record
          cur.execute("UPDATE device_limits SET min = %s, max = %s WHERE eui = %s AND parameter = %s;",
                      (mind or None, maxd or None, eui, p))
        else:
          # Insert a new record
          cur.execute("INSERT INTO device_limits (eui, parameter, min, max) VALUES (%s, %s, %s, %s);",
                      (eui, p, mind or None, maxd or None))

    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('devicegraph', dev=eui))
  else:
    return render_template("error.html", errorMessage="Error registrando dispositivo")

@app.route('/alerts')
def alerts():
  conn = get_db_connection()
  cur = conn.cursor()

  current_date = datetime.date.today()  # Get date as day-month-year
  current_date_str = current_date.strftime("%Y-%m-%d")
  
  # Get alerts received on the current day
  cur.execute('SELECT name, descrip, param, value, date '
              'FROM alerts '
              'NATURAL JOIN device '
              'WHERE DATE_TRUNC(\'day\', date) = %s '
              'ORDER BY date DESC;', (current_date_str,))
  current_day_alerts = cur.fetchall()

  # Get alerts received before the current day
  cur.execute('SELECT name, descrip, param, value, date '
              'FROM alerts '
              'NATURAL JOIN device '
              'WHERE DATE_TRUNC(\'day\', date) < %s '
              'ORDER BY date DESC;', (current_date_str,))
  previous_day_alerts = cur.fetchall()

  # Get Devices names
  cur.execute('SELECT eui, name '
              'FROM device '
              'WHERE eui IN (SELECT eui FROM alerts);')
  names = cur.fetchall()

  cur.close()
  conn.close()
  return render_template("alerts.html",
                         current_day_alerts=current_day_alerts,
                         previous_day_alerts=previous_day_alerts,
                         names=names[0])
