import asyncio
from transformers import BertTokenizer, BertForSequenceClassification, pipeline
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import matplotlib.pyplot as plt
from flask import Flask, request, jsonify

# 加載 .env 文件，確保 SUPABASE_URL 和 SUPABASE_KEY 被正確讀取
load_dotenv()

# 配置情緒分析模型 (使用 nlptown/bert-base-multilingual-uncased-sentiment 模型)
model_name = "nlptown/bert-base-multilingual-uncased-sentiment"
model = BertForSequenceClassification.from_pretrained(model_name)
tokenizer = BertTokenizer.from_pretrained(model_name)

# 創建情緒分析 pipeline
sentiment_analyzer = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

# Supabase 資訊
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 統計數據存儲
emotion_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
star_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

def bert_sentiment_analysis(news):
    """
    使用 nlptown 的多語言 BERT 模型進行情緒分析
    news: string 文章內容
    return: dict 包含 sentiment_score, star, 和 emotion (1: positive, 0: neutral, -1: negative)
    """
    result = sentiment_analyzer(news[:512])[0]  # 模型有 token 限制，這裡截取前512個字元
    sentiment_label = result['label']  # 例如 "5 stars"
    sentiment_score = result['score']  # 置信度分數

    # 提取星級數字，例如 "5 stars" -> 5
    star = int(sentiment_label.split()[0])

    # 根據星級設定情緒類型
    if star in [1, 2]:
        emotion = -1  # negative
        emotion_label = 'negative'
    elif star == 3:
        emotion = 0  # neutral
        emotion_label = 'neutral'
    else:
        emotion = 1  # positive
        emotion_label = 'positive'

    # 統計情緒類型和星級
    emotion_counts[emotion_label] += 1
    star_counts[star] += 1

    return {
        "score": sentiment_score,  # 置信度分數 (浮點數)
        "star": star,  # 星級 (1 到 5)
        "emotion": emotion  # 情緒類型 (1: positive, 0: neutral, -1: negative)
    }

async def fetch_data_by_date(table_name, date, batch_size=1000):
    """
    從 Supabase 表中按日期篩選數據，分批次提取數據
    """
    offset = 0
    all_data = []
    
    while True:
        response = (
            supabase.from_(table_name)
            .select("*")
            .eq("date", date)
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        data = response.data
        
        if not data:
            break  # 當沒有更多數據時，結束循環
        
        all_data.extend(data)
        offset += batch_size
        print(f"Fetched {len(data)} records from {table_name} for date {date}, total so far: {len(all_data)}")
    
    return all_data

async def analyze_and_store_sentiments(date):
    # 從 health_news 和 health_news_API 表中按日期提取數據
    news_data_health = await fetch_data_by_date("health_news", date)
    news_data_api = await fetch_data_by_date("health_news_API", date)

    # 合併來自兩個表的數據
    news_data = news_data_health + news_data_api

    if not news_data:
        print("No news data found for the specified date.")
        return

    for news in news_data:
        try:
            print(f"Processing news ID: {news['id']}")

            # 進行情緒分析
            sentiment_result = bert_sentiment_analysis(news["content"])
            sentiment_score = sentiment_result["score"]
            star = sentiment_result["star"]
            emotion = sentiment_result["emotion"]

            print(f"Sentiment for news ID {news['id']}: {star} stars ({emotion}), Score: {sentiment_score}")

            # 插入新的情緒分析結果
            insert_response = supabase.from_("health_news_sentiment").insert({
                "news_id": news["id"],
                "sentiment": sentiment_score,
                "star": star,
                "emotion": emotion
            }).execute()

            if insert_response.data:
                print(f"Successfully inserted sentiment for news ID: {news['id']}")
            else:
                print(f"Failed to insert sentiment for news ID {news['id']}. Response: {insert_response}")
                
        except Exception as e:
            print(f"Failed to process news ID {news['id']}. Error: {str(e)}")

def plot_statistics():
    """
    生成圖表，顯示情緒和星級分佈
    """
    plt.figure(figsize=(10, 5))

    # 情緒分佈圖表
    plt.subplot(1, 2, 1)
    emotions = list(emotion_counts.keys())
    emotion_values = list(emotion_counts.values())
    plt.bar(emotions, emotion_values, color=['#84C1FF', '#FFE66F', '#FF5151'])
    plt.title("Emotion Distribution")
    plt.xlabel("Emotion Type")
    plt.ylabel("Count")

    # 星級分佈圖表
    plt.subplot(1, 2, 2)
    stars = list(star_counts.keys())
    star_values = list(star_counts.values())
    plt.bar(stars, star_values, color='#84C1FF')
    plt.title("Star Rating Distribution")
    plt.xlabel("Star Rating")
    plt.ylabel("Count")

    plt.tight_layout()
    plt.show()

app = Flask(__name__)

@app.route("/analyze_health", methods=["POST"])
def analyze_health():
    data = request.get_json()
    date = data.get("date")

    if not date:
        return jsonify({"error": "Date not provided"}), 400

    asyncio.run(analyze_and_store_sentiments(date))
    plot_statistics()

    return jsonify({"message": "Sentiment analysis completed and chart generated."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
