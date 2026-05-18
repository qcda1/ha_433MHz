# Capture all detected 433MHz sensors and send data to Home Assistant via REST API
# Detected sensors are catalogued in sondes.yaml file
# Sensors to be sent to Home Assistant need to have follow: set to true
# When follow: true, sensor temperature and humidity is sent to Home Assistant
#
#
import subprocess
import json
import requests
import yaml
import os
import logging
from datetime import datetime

HA_URL = "http://192.168.2.19:8123"  # Adresse de ton Home Assistant
HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4OWYxMzY1YmI0ZDI0ZGYzYmI5NjVhYTQ4YmI5ZDYwNSIsImlhdCI6MTczOTA0NDM4NCwiZXhwIjoyMDU0NDA0Mzg0fQ.wmTmMiMikT4wDkIRHsI5GeRACQqdKFW9LWUYfh718Bs"
CONFIG_FILE = "sondes.yaml"
LOG_FILE    = "sondes.log"

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

# Configuration du logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()  # Affiche aussi dans le terminal
    ]
)
log = logging.getLogger(__name__)

def charger_config():
    """Charge le fichier YAML, le crée s'il n'existe pas."""
    if not os.path.exists(CONFIG_FILE):
        config_defaut = {"sondes": {}}
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(config_defaut, f, default_flow_style=False)
        log.info(f"Fichier {CONFIG_FILE} créé.")

    with open(CONFIG_FILE, "r") as f:
        return yaml.safe_load(f) or {"sondes": {}}

def sauvegarder_config(config):
    """Sauvegarde la config YAML."""
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

def enregistrer_sonde(config, data):
    """Ajoute ou met à jour une sonde dans le YAML avec tous les attributs reçus."""
    sensor_id = data.get("id")
    time_str  = data.get("time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    nouvelle = sensor_id not in config["sondes"]
    sonde    = config["sondes"].get(sensor_id, {})

    # Attributs de gestion — préservés si déjà existants
    sonde_update = {
        "name"              : sonde.get("name", f"Unknown sensor {sensor_id}"),
        "follow"            : sonde.get("follow", False),
        "last_reception"    : time_str,
    }

    # Tous les champs natifs retournés par rtl_433 sauf id et time
    champs_exclus = {"id", "time"}
    for cle, valeur in data.items():
        if cle not in champs_exclus:
            sonde_update[cle] = valeur

    sonde.update(sonde_update)
    config["sondes"][sensor_id] = sonde
    sauvegarder_config(config)

    if nouvelle:
        temperature = data.get("temperature_C")
        humidite    = data.get("humidity")
        modele      = data.get("model", "unknown")
        canal       = data.get("channel", "?")
        hum_str     = f"{humidite}%" if humidite is not None else "N/A"
        temp_str    = f"{temperature}°C" if temperature is not None else "N/A"
        log.info(f"New sensor added: "
                 f"ID={sensor_id} | {modele} | channel={canal} "
                 f"| temp={temp_str} | hum={hum_str}")

    return sonde

def envoyer_a_ha(sensor_id, name, temperature, humidite, batterie, modele, canal):
    """Crée ou met à jour les entités dans Home Assistant."""

    # Température — toujours envoyée
    requests.post(
        f"{HA_URL}/api/states/sensor.rtl433_{sensor_id}_temperature",
        headers=HEADERS,
        json={
            "state": temperature,
            "attributes": {
                "unit_of_measurement" : "°C",
                "friendly_name"       : f"{name} Temperature",
                "device_class"        : "temperature",
                "battery_low"         : batterie == 0,
                "model"               : modele,
                "channel"             : canal,
            }
        }
    )

    # Humidité — seulement si disponible
    if humidite is not None:
        requests.post(
            f"{HA_URL}/api/states/sensor.rtl433_{sensor_id}_humidity",
            headers=HEADERS,
            json={
                "state": humidite,
                "attributes": {
                    "unit_of_measurement" : "%",
                    "friendly_name"       : f"{name} Humidity",
                    "device_class"        : "humidity",
                    "battery_low"         : batterie == 0,
                    "model"               : modele,
                    "channel"             : canal,
                }
            }
        )

    # Batterie
    requests.post(
        f"{HA_URL}/api/states/binary_sensor.rtl433_{sensor_id}_battery",
        headers=HEADERS,
        json={
            "state": "on" if batterie == 0 else "off",
            "attributes": {
                "friendly_name": f"{name} Low battery",
                "device_class" : "battery",
                "model"        : modele,
                "channel"      : canal,
            }
        }
    )

    hum_str    = f"{humidite}%" if humidite is not None else "N/A"
    statut_bat = "LOW" if batterie == 0 else "OK"
    log.info(f"Sent to HA: {name} (ID={sensor_id}) "
             f"| {modele} | channel={canal} "
             f"| {temperature}°C | {hum_str} "
             f"| battery: {statut_bat}")

def lire_capteurs(timeout=90):
    """Lit tous les appareils sur la fréquence pendant <timeout> secondes."""
    cmd = ["rtl_433", "-F", "json", "-T", str(timeout)]

    process = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    appareils_vus = {}

    for ligne in process.stdout.splitlines():
        ligne = ligne.strip()
        if not ligne:
            continue
        try:
            data      = json.loads(ligne)
            sensor_id = data.get("id")

            if sensor_id is None:
                continue

            appareils_vus[sensor_id] = data

            temperature = data.get("temperature_C")
            humidite    = data.get("humidity")
            batterie    = data.get("battery_ok", 1)
            modele      = data.get("model", "?")
            canal       = data.get("channel", "?")
            hum_str     = f"{humidite}%" if humidite is not None else "N/A"
            temp_str    = f"{temperature}°C" if temperature is not None else "N/A"

            log.info(f"Received: ID={sensor_id} | {modele} | channel={canal} "
                     f"| temp={temp_str} | hum={hum_str} "
                     f"| battery={'OK' if batterie else 'LOW'}")

        except json.JSONDecodeError:
            pass

    return appareils_vus

if __name__ == "__main__":
    log.info(f"Listening for all devices for 90 seconds... on {datetime.now()}")

    config    = charger_config()
    appareils = lire_capteurs(timeout=90)

    log.info(f"{len(appareils)} device(s) detected.")

    for sensor_id, data in appareils.items():
        sonde_config = enregistrer_sonde(config, data)

        temperature = data.get("temperature_C")
        humidite    = data.get("humidity")
        batterie    = data.get("battery_ok", 1)
        modele      = data.get("model", "unknown")
        canal       = data.get("channel", "?")
        name        = sonde_config.get("name", f"Sensor {sensor_id}")
        follow      = sonde_config.get("follow", False)

        if not follow:
            log.debug(f"Ignored: {name} (ID={sensor_id})")
            continue

        if temperature is None:
            log.warning(f"ERROR: {name} (ID={sensor_id}) is marked "
                        f"'follow: true' but has no temperature sensor — ignored.")
            continue

        envoyer_a_ha(sensor_id, name, temperature, humidite,
                     batterie, modele, canal)

    log.info("Done.")