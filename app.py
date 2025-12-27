import os
import pickle
from datetime import date
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)


MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")

model = pickle.load(open(MODEL_PATH, "rb"))

MONGO_URI = os.environ.get("MONGO_URI")

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=3000  # ⏱ prevents silent hang
)

db = client["student_performance_db"]
collection = db["weekly_performance"]

# 🔍 force connection check
client.admin.command("ping")
print("MongoDB connected successfully")


@app.route("/", methods=["GET", "POST"])
def home():
    # ---------- POST ----------
    if request.method == "POST":
        hours = float(request.form["hours"])
        previous = float(request.form["previous"])
        extra = int(request.form["extra"])
        sleep = float(request.form["sleep"])
        papers = int(request.form["papers"])

        prediction = model.predict([[hours, previous, extra, sleep, papers]])[0]
        prediction = max(0, min(100, round(prediction, 2)))

        today = date.today().strftime("%Y-%m-%d")

        # ✅ upsert today's value
        collection.update_one(
            {"date": today},
            {"$set": {"performance": prediction}},
            upsert=True
        )

        return redirect(url_for("home", latest=prediction))

    # ---------- GET ----------
    records = list(collection.find().sort("date", 1))

    daily_map = {}
    for r in records:
        daily_map[r["date"]] = r["performance"]

    today = date.today().strftime("%Y-%m-%d")

    # ✅ ONE source of truth
    prediction = request.args.get("latest", type=float)

    if prediction is None and daily_map:
        prediction = daily_map[list(daily_map.keys())[-1]]

    # ✅ build chart AFTER final value is known
    sorted_items = sorted(daily_map.items(), key=lambda x: x[0])
    dates = [d for d, _ in sorted_items]
    scores = [s for _, s in sorted_items]

    return render_template(
        "index.html",
        prediction=prediction,
        dates=dates,
        scores=scores
    )
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

