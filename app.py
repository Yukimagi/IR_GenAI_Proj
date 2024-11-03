from flask import Flask, request, jsonify, render_template
import subprocess
import os
import logging
from utils import (
    analyze_data,
    analyze_realtime,
    plot_statistics,
    plot_sentiment_timeseries,
)
from datetime import datetime

current_file_path = os.path.abspath(__file__)

print(f"Current file path: {current_file_path}")

app = Flask(__name__)


@app.route("/about.html")
def about():
    return render_template("about.html")


@app.route("/index.html")
def index():
    return render_template("index.html")


@app.route("/crawl.html")
def crawl():
    return render_template("crawl.html")


@app.route("/emotion.html")
def emotion():
    return render_template("emotion.html")


@app.route("/")
def root():
    return render_template("index.html")


@app.route("/fetch_news", methods=["GET", "POST"])
def fetch_news():
    data = request.get_json()
    company = data.get("company")
    topic = data.get("topic")
    pages = data.get("pages")

    # 確定執行的腳本名稱
    script_map = {
        ("chinatimes", "stock"): "Proj_ChinaTimes/Proj_ChinaTimes_Stock.py",
        ("chinatimes", "health"): "Proj_ChinaTimes/Proj_ChinaTimes_health.py",
        ("chinatimes", "sports"): "Proj_ChinaTimes/Proj_ChinaTimes_sports.py",
        ("liberty", "stock"): "Proj_ltn/Proj_ltn_Stock.py",
        ("liberty", "health"): "Proj_ltn/Proj_ltn_health.py",
        ("liberty", "sports"): "Proj_ltn/Proj_ltn_sports.py",
        ("tvbs", "stock"): "Proj_tvbs/Proj_tvbs_Stock.py",
        ("tvbs", "health"): "Proj_tvbs/Proj_tvbs_health.py",
        ("tvbs", "sports"): "Proj_tvbs/Proj_tvbs_sports.py",
        ("api", "stock"): "Proj_API/stock_API_news.py",
        ("api", "health"): "Proj_API/health_API_news.py",
        ("api", "sports"): "Proj_API/sport_API_news.py",
    }

    script_name = script_map.get((company, topic))

    if script_name is None:
        return jsonify({"message": "Invalid company or topic"}), 400

    try:
        # 呼叫對應的 Python 檔案，並傳遞頁數參數
        result = subprocess.run(
            ["python", script_name, str(pages)], capture_output=True, text=True
        )

        # 檢查腳本執行狀態
        if result.returncode == 0:
            return jsonify({"message": "success"})
        else:
            return (
                jsonify(
                    {"message": "Error executing script", "details": result.stderr}
                ),
                500,
            )
    except Exception as e:
        return jsonify({"message": f"Server error: {str(e)}"}), 500


@app.route("/analyze", methods=["POST"])
def analyze():
    mode = request.form.get("mode")
    topic = request.form.get("topic")
    startDate = request.form.get("startDate")
    endDate = request.form.get("endDate")
    source = request.form.get("source")

    # Debugging statements
    print(
        f" Mode:{mode},Topic: {topic}, Start Date: {startDate}, End Date: {endDate}, Source: {source}"
    )

    # Validate topic selection and date format
    if topic not in ["health", "sport", "stock"]:
        return jsonify({"error": "Invalid topic selected."}), 400
    if source not in ["ltn", "tvbs", "China Times", "Yahoo Entertainment", "all"]:
        return jsonify({"error": "Invalid topic selected."}), 400

    # 檢查日期格式
    try:
        datetime.strptime(startDate, "%Y-%m-%d")
        datetime.strptime(endDate, "%Y-%m-%d")
    except ValueError as ve:
        return (
            jsonify(
                {"error": f"Invalid date format. Use YYYY-MM-DD. Error: {str(ve)}"}
            ),
            400,
        )
    global global_plot_data
    global_plot_data = {}  # Reset the global data structure

    if mode == "database":
        # 從資料庫取得已儲存的分析數據
        analyze_data(topic, startDate, endDate, source)

        # 繪製情緒分布和評分分布圖表
        chart_image = plot_statistics()

        # 繪製情緒隨時間變化的時間序列圖
        time_series_image = plot_sentiment_timeseries(topic, startDate, endDate, source)
    else:  # "realtime" 即時分析模式
        analyze_realtime(topic, startDate, endDate, source)

        # 繪製情緒分布和評分分布圖表
        chart_image = plot_statistics()

        # 繪製情緒隨時間變化的時間序列圖
        time_series_image = plot_sentiment_timeseries(topic, startDate, endDate, source)

    return jsonify({"chart": chart_image, "time_series": time_series_image})


if __name__ == "__main__":
    # 定義app在8080埠運行
    app.run(host="0.0.0.0", port=8000, debug=True)
