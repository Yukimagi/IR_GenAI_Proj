import asyncio
from supabase import create_client
from transformers import BertTokenizer, BertForSequenceClassification, pipeline
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import matplotlib.pyplot as plt

# 加載 .env 文件，確保 SUPABASE_URL 和 SUPABASE_KEY 被正確讀取
load_dotenv()

# 配置情緒分析模型 (使用 nlptown/bert-base-multilingual-uncased-sentiment 模型)
model_name = "nlptown/bert-base-multilingual-uncased-sentiment"
model = BertForSequenceClassification.from_pretrained(model_name)
tokenizer = BertTokenizer.from_pretrained(model_name)

# 創建情緒分析 pipeline
sentiment_analyzer = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

# Supabase 資訊
# Supabase info for Database 1
url1 = os.getenv("SUPABASE_URL_1")
key1 = os.getenv("SUPABASE_KEY_1")
supabase1 = create_client(url1, key1)

# Supabase info for Database 2
url2 = os.getenv("SUPABASE_URL_2")
key2 = os.getenv("SUPABASE_KEY_2")
supabase2 = create_client(url2, key2)

# 統計數據存儲
emotion_counts = {"positive": 0, "neutral": 0, "negative": 0}
star_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}


def bert_sentiment_analysis(news):
    """
    使用 nlptown 的多語言 BERT 模型進行情緒分析
    news: string 文章內容

    return: dict 包含 sentiment_score, star, 和 emotion (1: positive, 0: neutral, -1: negative)
    """
    result = sentiment_analyzer(news[:512])[0]  # 模型有 token 限制，這裡截取前512個字元
    sentiment_label = result["label"]  # 例如 "5 stars"
    sentiment_score = result["score"]  # 置信度分數

    # 提取星級數字，例如 "5 stars" -> 5
    star = int(sentiment_label.split()[0])

    # 根據星級設定情緒類型
    if star in [1, 2]:
        emotion = -1  # negative
        emotion_label = "negative"
    elif star == 3:
        emotion = 0  # neutral
        emotion_label = "neutral"
    else:
        emotion = 1  # positive
        emotion_label = "positive"

    # 統計情緒類型和星級
    emotion_counts[emotion_label] += 1
    star_counts[star] += 1

    return {
        "score": sentiment_score,  # 置信度分數 (浮點數)
        "star": star,  # 星級 (1 到 5)
        "emotion": emotion,  # 情緒類型 (1: positive, 0: neutral, -1: negative)
    }


####################### [date版本] ############################


async def fetch_data_within_date(
    topic, start_date, end_date, source="all", batch_size=5000
):
    """
    分批次從 Supabase 表中提取在指定日期範圍內的數據，直到提取完成。
    """
    all_data = []

    # 遍歷 supabase1 和 supabase2 數據庫
    for db_index, supabase in enumerate([supabase1, supabase2], start=1):
        # 遍歷 "news" 和 "news_API" 表
        for table_suffix in ["news", "news_API"]:
            table_name = f"{topic}_{table_suffix}"
            offset = 0

            while True:
                # 構建查詢並篩選日期範圍
                query = (
                    supabase.from_(table_name)
                    .select("*")  # 取得所需欄位
                    .gte("date", start_date)
                    .lte("date", end_date)
                    .range(offset, offset + batch_size - 1)
                )

                # 如果 source 參數不是 "all"，則進行來源篩選
                if source != "all":
                    query = query.eq("source", source)

                # 執行查詢
                response = query.execute()
                data = response.data

                # 檢查是否有數據
                if not data:
                    print(
                        f"No more data in {table_name} for date range {start_date} to {end_date}."
                    )
                    break

                # 如果返回 None，則說明發生錯誤
                if data is None:
                    print(f"Error fetching data from table: {table_name}")
                    break

                # 將數據添加到 all_data 中
                all_data.extend(data)
                offset += batch_size

                print(
                    f"Fetched {len(data)} records from {table_name} in supabase{db_index} for date range {start_date} to {end_date}, total so far: {len(all_data)}"
                )

    return all_data


async def analyze_and_store_sentiments(topic, start_date, end_date, source):
    print("即時情緒分析中!")

    # 從指定topic、source中提取在 start_date 和 end_date 之間的數據
    news_data = await fetch_data_within_date(topic, start_date, end_date, source)
    if not news_data:
        print(f"No news data found in {source} for the given date range.")
        return

    for news in news_data:
        try:
            # 檢查該 news_id 是否已存在於 {topic}_news_sentiment 表中
            existing_sentiment = (
                supabase2.from_(f"{topic}_news_sentiment")
                .select("id")
                .eq("news_id", news["id"])
                .execute()
            )

            # 如果該新聞的 sentiment 已存在，跳過分析
            if existing_sentiment.data:
                print(f"Skipping news ID {news['id']} - sentiment already exists.")
                continue

            print(f"Processing news ID: {news['id']}")

            # 進行情緒分析
            sentiment_result = bert_sentiment_analysis(news["content"])
            sentiment_score = sentiment_result["score"]
            star = sentiment_result["star"]
            emotion = sentiment_result["emotion"]

            print(
                f"Sentiment for news ID {news['id']}: {star} stars ({emotion}), Score: {sentiment_score}"
            )

            # 插入新的情緒分析結果
            insert_response = (
                supabase2.from_(f"{topic}_news_sentiment")
                .insert(
                    {
                        "news_id": news["id"],  # 將新聞的 id 傳入 news_id 欄位
                        "sentiment": sentiment_score,  # 儲存置信度分數 (浮點數)
                        "star": star,  # 儲存星級 (1 到 5)
                        "emotion": emotion,  # 儲存情緒類型 (-1, 0, 1)
                    }
                )
                .execute()
            )

            # 使用 response.data 確認是否成功插入數據
            if insert_response.data:
                print(f"Successfully inserted sentiment for news ID: {news['id']}")
            else:
                print(
                    f"Failed to insert sentiment for news ID {news['id']}. Response: {insert_response}"
                )

        except Exception as e:
            print(f"Failed to process news ID {news['id']}. Error: {str(e)}")


"""

def main(topic, start_date, end_date, source="all"):
    
    #Main entry point for sentiment analysis and storage for a specified topic.

    print(f"Starting sentiment analysis for topic: {topic}")
    asyncio.run(analyze_and_store_sentiments(topic, start_date, end_date, source))
    print("Sentiment analysis completed.")

if __name__ == "__main__":
    # Replace with desired values
    topic = "sport"  # Example topic
    start_date = "2024-09-25"  # Example start date
    end_date = "2024-10-01"  # Example end date
    source = "all"  # Example source; can specify or use "all" for all sources

    main(topic, start_date, end_date, source)
"""
