from flask import Flask, render_template, jsonify
import requests
import os
from datetime import datetime

app = Flask(__name__)

# =========================================================
# THINGSPEAK CONFIGURATION
# =========================================================

# Put your ThingSpeak Channel ID here
THINGSPEAK_CHANNEL_ID = os.environ.get(
    "THINGSPEAK_CHANNEL_ID",
    "3509954"
)

# Required only if your ThingSpeak channel is PRIVATE
THINGSPEAK_READ_API_KEY = os.environ.get(
    "OPACCU93TLYSVJT1",
    ""
)

# Number of historical readings to retrieve
THINGSPEAK_RESULTS = 50


# =========================================================
# THINGSPEAK URL
# =========================================================

def get_thingspeak_url():

    url = (
        f"https://api.thingspeak.com/"
        f"channels/{THINGSPEAK_CHANNEL_ID}/feeds.json"
    )

    params = {
        "results": THINGSPEAK_RESULTS
    }

    # Add Read API key only when supplied
    if THINGSPEAK_READ_API_KEY:
        params["api_key"] = THINGSPEAK_READ_API_KEY

    return url, params


# =========================================================
# READ THINGSPEAK DATA
# =========================================================

def read_thingspeak():

    try:

        url, params = get_thingspeak_url()

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        return data

    except requests.exceptions.RequestException as e:

        print("ThingSpeak connection error:", e)

        return None

    except ValueError as e:

        print("ThingSpeak JSON error:", e)

        return None


# =========================================================
# CONVERT THINGSPEAK FEEDS
# =========================================================

def process_feeds(data):

    if not data or "feeds" not in data:

        return []

    processed = []

    for feed in data["feeds"]:

        try:

            temperature = (
                float(feed["field1"])
                if feed.get("field1") not in [None, ""]
                else None
            )

            humidity = (
                float(feed["field2"])
                if feed.get("field2") not in [None, ""]
                else None
            )

            sound = (
                float(feed["field3"])
                if feed.get("field3") not in [None, ""]
                else None
            )

            weight = (
                float(feed["field4"])
                if feed.get("field4") not in [None, ""]
                else None
            )

            status_code = (
                int(float(feed["field5"]))
                if feed.get("field5") not in [None, ""]
                else 1
            )

            # Convert status number into readable text
            if status_code == 3:
                status = "ALERT"

            elif status_code == 2:
                status = "ATTENTION"

            else:
                status = "NORMAL"

            processed.append({

                "entry_id": feed.get("entry_id"),

                "created_at": feed.get("created_at"),

                "temperature": temperature,

                "humidity": humidity,

                "sound": sound,

                "weight": weight,

                "status_code": status_code,

                "status": status

            })

        except (ValueError, TypeError):

            continue

    return processed


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def dashboard():

    return render_template(
        "dashboard.html"
    )


# =========================================================
# API - ALL THINGSPEAK DATA
# =========================================================

@app.route("/api/data")
def api_data():

    data = read_thingspeak()

    if data is None:

        return jsonify({

            "success": False,

            "message": "Unable to connect to ThingSpeak",

            "data": []

        }), 503

    feeds = process_feeds(data)

    return jsonify({

        "success": True,

        "channel": data.get("channel", {}),

        "data": feeds,

        "count": len(feeds),

        "last_updated": (
            feeds[-1]["created_at"]
            if feeds
            else None
        )

    })


# =========================================================
# API - LATEST READING
# =========================================================

@app.route("/api/latest")
def api_latest():

    data = read_thingspeak()

    if data is None:

        return jsonify({

            "success": False,

            "message": "Unable to connect to ThingSpeak"

        }), 503

    feeds = process_feeds(data)

    if not feeds:

        return jsonify({

            "success": False,

            "message": "No ThingSpeak data available"

        }), 404

    latest = feeds[-1]

    return jsonify({

        "success": True,

        "data": latest

    })


# =========================================================
# API - CHANNEL INFORMATION
# =========================================================

@app.route("/api/channel")
def api_channel():

    data = read_thingspeak()

    if data is None:

        return jsonify({

            "success": False,

            "message": "Unable to connect to ThingSpeak"

        }), 503

    channel = data.get("channel", {})

    return jsonify({

        "success": True,

        "channel": {

            "id": channel.get("id"),

            "name": channel.get("name"),

            "description": channel.get("description"),

            "field1": channel.get("field1"),

            "field2": channel.get("field2"),

            "field3": channel.get("field3"),

            "field4": channel.get("field4"),

            "field5": channel.get("field5"),

            "updated_at": channel.get("updated_at"),

            "last_entry_id": channel.get("last_entry_id")

        }

    })


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return jsonify({

        "status": "online",

        "application": "BeeGuard Smart Beehive Monitoring System",

        "server_time": datetime.utcnow().isoformat() + "Z"

    })


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    return jsonify({

        "success": False,

        "error": "Page not found"

    }), 404


@app.errorhandler(500)
def internal_error(error):

    return jsonify({

        "success": False,

        "error": "Internal server error"

    }), 500


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )