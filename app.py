from flask import Flask, request, jsonify, render_template
import subprocess
import os

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
        ("chinatimes", "stock"): "test1.py",
        ("chinatimes", "health"): "test2.py",
        ("chinatimes", "sports"): "test3.py",
        ("liberty", "stock"): "test4.py",
        ("liberty", "health"): "test5.py",
        ("liberty", "sports"): "test6.py",
        ("tvbs", "stock"): "test7.py",
        ("tvbs", "health"): "test8.py",
        ("tvbs", "sports"): "test9.py",
        ("api", "stock"): "test10.py",
        ("api", "health"): "test11.py",
        ("api", "sports"): "test12.py"
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
    


