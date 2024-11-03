# utils.py
from supabase import create_client
from dotenv import load_dotenv
import os
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import pandas as pd

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

emotion_counts = {"positive": 0, "neutral": 0, "negative": 0}
star_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}


def fetch_news_ids(topic, start_date, end_date, source, batch_size=5000):
    # 從 `{topic}_news` 和 `{topic}_news_API` 兩個資料表中篩選符合條件的數據
    news_ids = set()
    for db_index, supabase in enumerate([supabase1, supabase2], start=1):
        for table_suffix in ["news", "news_API"]:
            table_name = f"{topic}_{table_suffix}"
            offset = 0
            while True:
                query = (
                    supabase.from_(table_name)
                    .select("id")
                    .gte("date", start_date)
                    .lte("date", end_date)
                    .range(offset, offset + batch_size - 1)
                )

                # If source is not "all", filter by the specific source
                if source != "all":
                    query = query.eq("source", source)

                response = query.execute()

                if response.data is None:
                    print(f"Error fetching data from table: {table_name}")
                    break

                data = response.data
                if not data:
                    break

                # 將符合條件的新聞 ID 添加到 news_ids 集合中
                news_ids.update((db_index, item["id"]) for item in data)
                offset += batch_size
    return list(news_ids)


def fetch_sentiment_data(news_ids, topic, batch_size=5000):
    # 確保使用正確的情緒分析表名稱
    sentiment_table = f"{topic}_news_sentiment"
    all_sentiments = []
    fetched_ids = set()  # 記錄已抓取的 (db_index, news_id)，避免重複

    for db_index, supabase in enumerate([supabase1, supabase2], start=1):
        batch_ids = [news_id for db_id, news_id in news_ids if db_id == db_index]

        for i in range(0, len(batch_ids), batch_size):
            batch = batch_ids[i : i + batch_size]
            response = (
                supabase.from_(sentiment_table)
                .select("news_id", "sentiment", "emotion", "star")
                .in_("news_id", batch)
                .execute()
            )

            # 確認回應資料是否存在
            if response.data:
                for entry in response.data:
                    id_with_db = (db_index, entry["news_id"])
                    if id_with_db not in fetched_ids:
                        entry["db_index"] = db_index  # 新增來源資料庫的標記
                        all_sentiments.append(entry)
                        fetched_ids.add(id_with_db)  # 記錄已處理的 (db_index, news_id)
    return all_sentiments


def fetch_date_data(news_ids, topic, batch_size=5000):
    all_dates = []
    fetched_ids = set()  # Track fetched (db_index, news_id) to avoid duplicates

    for db_index, supabase in enumerate([supabase1, supabase2], start=1):
        batch_ids = [news_id for db_id, news_id in news_ids if db_id == db_index]

        for i in range(0, len(batch_ids), batch_size):
            batch = batch_ids[i : i + batch_size]

            # Loop through table suffixes
            for table_suffix in ["news", "news_API"]:
                table_name = f"{topic}_{table_suffix}"

                # Query the current table
                response = (
                    supabase.from_(table_name)
                    .select("id", "date")
                    .in_("id", batch)
                    .execute()
                )

                # Process response
                if response.data:
                    for entry in response.data:
                        id_with_db = (db_index, entry["id"])
                        if id_with_db not in fetched_ids:
                            entry["db_index"] = db_index  # 新增來源資料庫的標記
                            all_dates.append(entry)
                            fetched_ids.add(id_with_db)

    return all_dates


def analyze_data(topic, start_date, end_date, source):
    global emotion_counts, star_counts
    emotion_counts = {"positive": 0, "neutral": 0, "negative": 0}
    star_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    # 抓取符合條件的新聞 ID 和對應情緒數據
    news_ids = fetch_news_ids(topic, start_date, end_date, source)
    sentiment_data = fetch_sentiment_data(news_ids, topic)

    # 分析資料並累積計數，同時列印每個 ID 的情緒和星級
    for entry in sentiment_data:
        db_index = entry["db_index"]
        news_id = entry["news_id"]
        star = entry["star"]
        emotion = entry["emotion"]

        # 列印每筆資料的來源資料庫、ID、star 和 emotion
        print(
            f"Database: {db_index}, News ID: {news_id}, Star: {star}, Emotion: {emotion}"
        )

        # 累計 star 和 emotion 計數
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
    axes[0].bar(emotions, emotion_values, color=["#84C1FF", "#FFE66F", "#FF5151"])
    axes[0].set_title("Emotion Distribution")
    axes[0].set_xlabel("Emotion Type")
    axes[0].set_ylabel("Count")

    # Star Rating Distribution
    stars = list(star_counts.keys())
    star_values = list(star_counts.values())
    axes[1].bar(stars, star_values, color="#CA8EFF")
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


# 按時間順序繪製這些情緒變化
def plot_sentiment_timeseries(topic, start_date, end_date, source):
    # Retrieve the relevant news IDs and their associated dates
    news_ids = fetch_news_ids(topic, start_date, end_date, source)
    news_dates = fetch_date_data(
        news_ids, topic
    )  # Returns "news_id", "date", "db_index"
    sentiment_data = fetch_sentiment_data(
        news_ids, topic
    )  # Returns "news_id", "sentiment", "emotion", "star", "db_index"

    # Convert lists to DataFrames for easier merging
    news_dates_df = pd.DataFrame(news_dates)
    sentiment_data_df = pd.DataFrame(sentiment_data)

    print("news_dates_df columns:", news_dates_df.columns)
    print("sentiment_data_df columns:", sentiment_data_df.columns)

    # 合併時指定不同的欄位名稱
    combined_data = pd.merge(
        news_dates_df, sentiment_data_df, left_on="id", right_on="news_id", how="inner"
    )

    # Confirm the data contains the "date" column; otherwise, return an error message
    if "date" not in combined_data.columns:
        print("No date information available in the sentiment data.")
        return None

    # Convert the date column to datetime format and sort by date
    combined_data["date"] = pd.to_datetime(combined_data["date"])
    combined_data = combined_data.sort_values("date")

    # Calculate the daily average sentiment score
    daily_sentiment = combined_data.groupby("date")["sentiment"].mean()

    # Plot
    fig, ax = plt.subplots(figsize=(10, 5))
    daily_sentiment.plot(ax=ax, color="#84C1FF", linestyle="-")
    ax.set_title(f"Sentiment Trend from {start_date} to {end_date}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Average Sentiment")
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.5)  # Neutral sentiment line
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Convert the plot to a Base64-encoded PNG image
    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return image_base64
