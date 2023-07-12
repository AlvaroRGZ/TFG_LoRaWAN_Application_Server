# TFG - LoRaWAN Network server and data visualization aplication.

## Author
* Álvaro Rodríguez Gómez (alu0101362953@ull.edu.es)

### Summary
Code for the deployment of the LoRaWAN network data access application.
> [TFG document](https://docs.google.com/document/d/17de5QwZpcAu96HxHWc-FqdTdwWI_GXkvmO4ht0hp0cQ/edit?usp=gmail)

### Requirements
You must create 2 files:
- *.mapbox_token:* where to put your map box token for maps.
- *.telegram_bot_token:* where to put your telegram bot token to have access to telegram API.

### Virtual enviroment packages
Once you have installed python and activated the virtual enviroment, you will have to install
the following packages:
```
pip3 install flask paho-mqtt pandas plotly requests fiona shapely pyproj rtree
```

