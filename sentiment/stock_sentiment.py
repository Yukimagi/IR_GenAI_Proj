import asyncio
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
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

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


async def fetch_all_data(table_name, batch_size=1000):
    """
    分批次從 Supabase 表中提取數據，直到提取完成。
    """
    offset = 0
    all_data = []

    while True:
        response = (
            supabase.from_(table_name)
            .select("*")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        data = response.data

        if not data:
            # 當沒有更多數據時，結束循環
            break

        all_data.extend(data)
        offset += batch_size

        print(
            f"Fetched {len(data)} records from {table_name}, total so far: {len(all_data)}"
        )

    return all_data


async def analyze_and_store_sentiments():
    # 從 stock_news 表中提取所有數據 (stock_news_API 表中的數據也會被提取)
    news_data_stock = await fetch_all_data("stock_news")

    # 合併來自兩個表的數據
    news_data = news_data_stock

    if not news_data:
        print("No news data found in stock_news.")
        return

    for news in news_data:
        try:
            print(f"Processing news ID: {news['id']}")

            # 進行情緒分析
            sentiment_result = bert_sentiment_analysis(news["content"])
            sentiment_score = sentiment_result["score"]
            star = sentiment_result["star"]
            emotion = sentiment_result["emotion"]

            print(
                f"Sentiment for news ID {news['id']}: {star} stars ({emotion}), Score: {sentiment_score}"
            )

            # # 檢查該 news_id 是否已存在於 stock_news_sentiment 表中
            # existing_sentiment = supabase.from_("stock_news_sentiment").select("id").eq("news_id", news["id"]).execute()

            # # 如果該新聞已存在，則刪除舊記錄
            # if existing_sentiment.data:
            #     supabase.from_("stock_news_sentiment").delete().eq("news_id", news["id"]).execute()
            #     print(f"Deleted old sentiment analysis for news ID: {news['id']}")

            # 插入新的情緒分析結果
            insert_response = (
                supabase.from_("stock_news_sentiment")
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


def plot_statistics():
    """
    生成圖表，顯示情緒和星級分佈
    """
    # 情緒分佈圖表
    plt.figure(figsize=(10, 5))

    plt.subplot(1, 2, 1)
    emotions = list(emotion_counts.keys())
    emotion_values = list(emotion_counts.values())
    plt.bar(emotions, emotion_values, color=["#84C1FF", "#FFE66F", "#FF5151"])
    plt.title("Emotion Distribution")
    plt.xlabel("Emotion Type")
    plt.ylabel("Count")

    # 星級分佈圖表
    plt.subplot(1, 2, 2)
    stars = list(star_counts.keys())
    star_values = list(star_counts.values())
    plt.bar(stars, star_values, color="#84C1FF")
    plt.title("Star Rating Distribution")
    plt.xlabel("Star Rating")
    plt.ylabel("Count")

    plt.tight_layout()
    plt.show()


def main():
    """
    主程式入口，負責觸發情緒分析和存儲過程，並在完成後生成圖表
    """
    print("Starting sentiment analysis...")
    asyncio.run(analyze_and_store_sentiments())
    print("Sentiment analysis completed.")

    # 在分析完成後生成統計圖表
    plot_statistics()


if __name__ == "__main__":
    main()
