from flask import Flask, request, jsonify, render_template
import subprocess
import os
import logging

current_file_path = os.path.abspath(__file__)

print(f"Current file path: {current_file_path}")

app = Flask(__name__)

@app.route("/model.html")
def model():
    return render_template("model.html")

@app.route("/predict.html")
def predict():
    return render_template("predict.html")

@app.route("/about.html")
def about():
    return render_template("about.html")

@app.route("/contact.html")
def contact():
    return render_template("contact.html")

@app.route("/index.html")
def index():
    return render_template("index.html")

@app.route("/crawl.html")
def crawl():
    return render_template("crawl.html")

@app.route("/")
def root():
    return render_template("index.html")
    
@app.route("/fetch_news",methods=["GET", "POST"])
def fetch_news():
    data = request.get_json()
    company = data.get('company')
    topic = data.get('topic')
    pages = data.get('pages')

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
        ("api", "sports"): "Proj_API/sport_API_news.py"
    }
    
    script_name = script_map.get((company, topic))
    
    if script_name is None:
        return jsonify({"message": "Invalid company or topic"}), 400

    try:
        # 呼叫對應的 Python 檔案，並傳遞頁數參數
        result = subprocess.run(['python', script_name, str(pages)], capture_output=True, text=True)
        
        # 檢查腳本執行狀態
        if result.returncode == 0:
            return jsonify({"message": "success"})
        else:
            return jsonify({"message": "Error executing script", "details": result.stderr}), 500
    except Exception as e:
        return jsonify({"message": f"Server error: {str(e)}"}), 500

    
    
if __name__ == '__main__':
    #定義app在8080埠運行
    app.run(host="0.0.0.0",port=8000,debug=True)
    


