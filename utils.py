# utils.py
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import matplotlib.pyplot as plt
from io import BytesIO
import base64

# Load environment variables
load_dotenv()

# Supabase info for Database 1
url1 = os.getenv("SUPABASE_URL_1")
key1 = os.getenv("SUPABASE_KEY_1")
supabase1 = create_client(url1, key1)

# Supabase info for Database 2
url2 = os.getenv("SUPABASE_URL_2")
key2 = os.getenv("SUPABASE_KEY_2")
supabase2 = create_client(url2, key2)

emotion_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
star_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

def fetch_news_ids(topic, start_date, end_date, batch_size=5000):
    # 從 `{topic}_news` 和 `{topic}_news_API` 兩個資料表獲取 ID
    news_ids = set()
    for supabase in [supabase1, supabase2]: 
        for table_suffix in ["news", "news_API"]:
            table_name = f"{topic}_{table_suffix}"
            offset = 0
            while True:
                response = (
                    supabase.from_(table_name)
                    .select("id")
                    .gte("date", start_date)
                    .lte("date", end_date)
                    .range(offset, offset + batch_size - 1)
                    .execute()
                )

                print("response: ",response.data)
                # 確認有獲取到數據
                if response.data is None:
                    print(f"Error fetching data from table: {table_name}")
                    break

                data = response.data
                if not data:
                    break

                # 使用集合避免重複 ID
                news_ids.update(item["id"] for item in data)
                offset += batch_size
    return list(news_ids)

def fetch_sentiment_data(news_ids, topic, batch_size=5000):
    # 確保使用正確的情緒分析表名稱
    sentiment_table = f"{topic}_news_sentiment"
    all_sentiments = []
    for supabase in [supabase1, supabase2]: 
        for i in range(0, len(news_ids), batch_size):
            batch_ids = news_ids[i:i + batch_size]
            response = (
                supabase.from_(sentiment_table)
                .select("*")
                .in_("news_id", batch_ids)
                .execute()
            )
            
            # 確認回應資料是否存在
            if response.data:
                all_sentiments.extend(response.data)
    return all_sentiments

def analyze_data(topic, start_date, end_date):
    global emotion_counts, star_counts
    emotion_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
    star_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    
    # 抓取符合條件的新聞 ID 和對應情緒數據
    news_ids = fetch_news_ids(topic, start_date, end_date)
    sentiment_data = fetch_sentiment_data(news_ids, topic)
    
    # 分析資料並累積計數
    for entry in sentiment_data:
        star = entry["star"]
        emotion = entry["emotion"]
        star_counts[star] += 1
        if emotion == 1:
            emotion_counts["positive"] += 1
        elif emotion == 0:
            emotion_counts["neutral"] += 1
        elif emotion == -1:
            emotion_counts["negative"] += 1

def plot_statistics():
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))

    # Emotion Distribution
    emotions = list(emotion_counts.keys())
    emotion_values = list(emotion_counts.values())
    axes[0].bar(emotions, emotion_values, color=['#84C1FF', '#FFE66F', '#FF5151'])
    axes[0].set_title("Emotion Distribution")
    axes[0].set_xlabel("Emotion Type")
    axes[0].set_ylabel("Count")

    # Star Rating Distribution
    stars = list(star_counts.keys())
    star_values = list(star_counts.values())
    axes[1].bar(stars, star_values, color='#CA8EFF')
    axes[1].set_title("Star Rating Distribution")
    axes[1].set_xlabel("Star Rating")
    axes[1].set_ylabel("Count")

    plt.tight_layout()
    
    # Convert the plot to PNG image
    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return image_base64
