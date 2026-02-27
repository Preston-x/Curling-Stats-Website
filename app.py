from flask import Flask, render_template, request, jsonify
import pandas as pd
import os

app = Flask(__name__)

# Load CSV
df = pd.read_csv("Shot+ Database.csv")

# Ensure numeric columns
df["Shots"] = pd.to_numeric(df["Shots"], errors="coerce").fillna(0)
df["Shot+"] = pd.to_numeric(df["Shot+"], errors="coerce").fillna(0)
df["Tournament Rating"] = pd.to_numeric(df["Tournament Rating"], errors="coerce").fillna(100)

# ----- Routes -----
@app.route("/")
def home():
    return render_template("index.html")  # original search page

@app.route("/leaderboard_page")
def leaderboard_page():
    return render_template("leaderboard.html")  # new leaderboard page

@app.route("/search")
def search():
    name = request.args.get("player", "").strip()
    if not name:
        return jsonify([])

    # Filter player (case-insensitive)
    mask = df["Player"].str.contains(name, case=False, na=False)
    results = df[mask].copy()
    if results.empty:
        return jsonify([])

    # Ensure numeric columns
    results["Shots"] = pd.to_numeric(results["Shots"], errors="coerce").fillna(0)
    results["Shot+"] = pd.to_numeric(results["Shot+"], errors="coerce").fillna(0)
    results["Tournament Rating"] = pd.to_numeric(results["Tournament Rating"], errors="coerce").fillna(100)

    # Calculate Adjusted Rating
    results["Adjusted Rating"] = (results["Shot+"] * results["Tournament Rating"] / 100).fillna(0)

    # Extract year from Tournament (assumes year is in the string)
    results["Year"] = results["Tournament"].str.extract(r"(\d{4})")[0].astype(float)

    # Build result list per tournament
    result_list = []
    for _, row in results.iterrows():
        result_list.append({
            "Player": row["Player"],
            "Tournament": row["Tournament"],
            "Tournament Rating": float(row["Tournament Rating"]),
            "Shots": float(row["Shots"]),
            "Shot+": float(row["Shot+"]),
            "Adjusted Rating": round(float(row["Adjusted Rating"]), 2),
            "Year": int(row["Year"])
        })

    # Calculate subtotals per year
    subtotals = []
    for year, group in results.groupby("Year"):
        total_shots = group["Shots"].sum()
        if total_shots > 0:
            weighted_shot_plus = (group["Shot+"] * group["Shots"]).sum() / total_shots
            weighted_tr = (group["Tournament Rating"] * group["Shots"]).sum() / total_shots
            weighted_adj = (group["Adjusted Rating"] * group["Shots"]).sum() / total_shots
        else:
            weighted_shot_plus = weighted_tr = weighted_adj = 0

        subtotals.append({
            "Player": f"TOTAL {int(year)}",
            "Tournament": "-",
            "Tournament Rating": round(weighted_tr, 2),
            "Shots": float(total_shots),
            "Shot+": round(weighted_shot_plus, 2),
            "Adjusted Rating": round(weighted_adj, 2),
            "Year": int(year)
        })

    # Overall total
    total_shots = results["Shots"].sum()
    if total_shots > 0:
        weighted_shot_plus = (results["Shot+"] * results["Shots"]).sum() / total_shots
        weighted_tr = (results["Tournament Rating"] * results["Shots"]).sum() / total_shots
        weighted_adj = (results["Adjusted Rating"] * results["Shots"]).sum() / total_shots
    else:
        weighted_shot_plus = weighted_tr = weighted_adj = 0

    summary_row = {
        "Player": "TOTAL",
        "Tournament": "-",
        "Tournament Rating": round(weighted_tr, 2),
        "Shots": float(total_shots),
        "Shot+": round(weighted_shot_plus, 2),
        "Adjusted Rating": round(weighted_adj, 2),
        "Year": 0
    }

    # Combine all rows
    result_list.extend(subtotals)
    result_list.append(summary_row)

    return jsonify(result_list)

@app.route("/leaderboard")
def leaderboard():
    # Calculate Adjusted Rating per row
    df["Adjusted Rating"] = (df["Shot+"] * df["Tournament Rating"] / 100).fillna(0)

    # Group by player
    leaderboard_df = df.groupby("Player").apply(lambda x: pd.Series({
        "Total Shots": x["Shots"].sum(),
        "Weighted Shot+": (x["Shot+"] * x["Shots"]).sum() / max(x["Shots"].sum(), 1),
        "Weighted Tournament Rating": (x["Tournament Rating"] * x["Shots"]).sum() / max(x["Shots"].sum(), 1),
        "Adjusted Rating": (x["Adjusted Rating"] * x["Shots"]).sum() / max(x["Shots"].sum(), 1)
    })).reset_index()

    leaderboard_df = leaderboard_df.sort_values("Adjusted Rating", ascending=False)
    leaderboard_df["Adjusted Rating"] = leaderboard_df["Adjusted Rating"].round(2)
    leaderboard_df["Weighted Shot+"] = leaderboard_df["Weighted Shot+"].round(2)
    leaderboard_df["Weighted Tournament Rating"] = leaderboard_df["Weighted Tournament Rating"].round(2)

    return leaderboard_df.to_json(orient="records")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)