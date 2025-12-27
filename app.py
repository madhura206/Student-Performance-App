import os
import pickle
from datetime import date
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
import gdown

# --------------------
# Paths
# --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

# --------------------
# Model handling (Cloud-safe)
# --------------------
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")

if not os.path.exists(MODEL_PATH):
    print("Downloading model...")
    url = "https://drive.google.com/uc?id=12jhlGDWxbmjl8MK1UsHYYVhJmBV1tmhV"
    gdown.download(url, MODEL_PATH, quiet=False)

model = pickle.load(open(MODEL_PATH, "rb"))

# --------------------
# MongoDB (Safe init)
# --------------------
MONGO_URI = os.environ.get("MONGO_URI")

collection = None
if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        db = client["student_performance_db"]
        collection = db["weekly_performance"]
        print("MongoDB connected")
    except Exception as e:
        print("MongoDB connection failed:", e)

# --------------------
# Routes
# --------------------
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        hours = float(request.form["hours"])
        previous = float(request.form["previous"])
        extra = int(request.form["extra"])
        sleep = float(request.form["sleep"])
        papers = int(request.form["papers"])

        prediction = model.predict([[hours, previous, extra, sleep, papers]])[0]
        prediction = max(0, min(100, round(prediction, 2)))

        today = date.today().strftime("%Y-%m-%d")

        if collection is not None:
            collection.update_one(
                {"date": today},
                {"$set": {"performance": prediction}},
                upsert=True
            )

        return redirect(url_for("home", latest=prediction))

    # ---------- GET ----------
    daily_map = {}

    if collection is not None:
        records = list(collection.find().sort("date", 1))
        for r in records:
            daily_map[r["date"]] = r["performance"]

    prediction = request.args.get("latest", type=float)

    if prediction is None and daily_map:
        prediction = list(daily_map.values())[-1]

    dates = list(daily_map.keys())
    scores = list(daily_map.values())

    return render_template(
        "index.html",
        prediction=prediction,
        dates=dates,
        scores=scores
    )

# --------------------
# Local run only
# --------------------
if __name__ == "__main__":
    app.run()
