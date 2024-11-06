import sys
import requests
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import google.generativeai as genai
from google.ai.generativelanguage_v1 import HarmCategory
from google.generativeai.types import HarmBlockThreshold

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from datetime import datetime
import os
from dotenv import load_dotenv
from urllib.parse import quote
import random
import time

import asyncio
from datetime import datetime, timedelta
import google.generativeai as genai
from langchain.schema.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from google.generativeai.types import HarmBlockThreshold
from google.ai.generativelanguage_v1 import HarmCategory

import datetime

import io

# 設置標準輸出的編碼
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# Load environment variables
load_dotenv()

# Supabase settings
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# API Key and URL
#API_KEY = os.getenv("NEWS_API_KEY") 
#NEWS_API_URL = f"https://newsapi.org/v2/everything?q=台積電&from=2024-09-22&to=2024-10-21&sortBy=popularity&apiKey={API_KEY}&language=zh"

# Get all sport IDs from Supabase
def get_all_sport_ids():
    sports_response = supabase.table("sport").select("sportID").execute()
    if not sports_response or not sports_response.data:
        print("Error fetching sport IDs:", sports_response)
        return []
    return sports_response.data

# Get sport name by ID
def get_sport_name(sport_id):
    try:
        response = supabase.table('sport').select('sport_name').eq('sportID', sport_id).execute()
        if response.data:
            return response.data[0]['sport_name']
    except Exception as e:
        print(f"Error fetching sport name for {sport_id}: {e}")
    return None

# Use Gemini AI to determine whether the news is sport-related
def gemini_response(news, title, sport_name):
    model = 'gemini-1.5-flash'
    temperature = 1
    top_p = 0.9
    seed = 0
    load_dotenv()

    # 創建 Gemini 的 LLM 對象
    llm = ChatGoogleGenerativeAI(
                    google_api_key=os.getenv('GEMINI_API_KEY'),
                    model=model,
                    temperature=temperature,
                    top_p=top_p,
                    seed=seed,
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    }
                )
    
    prompt = f"""
    以下是今天的新聞資訊。請根據這些資訊判斷其是否是運動新聞，如果不是請回答無關：

    標題:
    {title}

    文章內容:
    {news}
    """

    try:
        # 嘗試調用 Gemini API
        response = llm.invoke(prompt)
        response_content = response.content
        print(response_content.strip())
        if "無關" in response_content:
            return "非運動新聞"
    except Exception as e:
        logging.error(f"Gemini API error: {e}")
        if "ResourceExhausted" in str(e) or "429" in str(e):
            logging.warning("API quota exhausted, switching to keyword matching.")
        else:
            logging.error("Unknown error, retrying in 5 seconds.")
            time.sleep(5)
            return gemini_response(news, title, sport_name, keywords)  # 重試

    
    # 替代方案：直接判斷新聞內容是否包含股票名稱
    if sport_name not in news and sport_name not in title:
        return "非運動新聞"
    
    return "運動新聞"



# Fetch news articles
def fetch_news(KEYWORD):
    # 計算過去一個月的日期範圍
    today = datetime.date.today()
    one_month_ago = today - datetime.timedelta(days=30)

    # 格式化日期 (YYYY-MM-DD)
    today_str = today.strftime('%Y-%m-%d')
    one_month_ago_str = one_month_ago.strftime('%Y-%m-%d')
    # API Key and URL
    API_KEY = os.getenv("NEWS_API_KEY") 
    NEWS_API_URL = f"https://newsapi.org/v2/everything?q={KEYWORD}&from={one_month_ago_str}&to={today_str}&sortBy=popularity&apiKey={API_KEY}&language=zh"
    response = requests.get(NEWS_API_URL)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        return response.json().get("articles", [])  # Updated to access "articles" instead of "results"
    return []

def insert_news_if_not_exists(sport_id, title, news_date, content, source, news_url):
    # 檢查是否已存在相同的記錄
    check_response = supabase.table("sport_news").select("*").eq("sportID", sport_id)\
        .eq("title", title)\
        .eq("date", news_date)\
        .eq("content", content)\
        .eq("source", source).execute()
    
    # 如果沒有找到重複的記錄，才進行插入
    if not check_response.data:
        insert_response = supabase.table("sport_news").insert({
            "sportID": int(sport_id),
            "title": title,
            "date": news_date,
            "content": content,
            "source": source,  
            "url": news_url
        }).execute()
        
        print(f"Inserted news: {title} for sport ID: {sport_id}")
        print(f"Insert Response: {insert_response}")
    else:
        print(f"Duplicate news found for sport ID: {sport_id}. Skipping insertion.")

# Main process
def main():
    sport_ids = get_all_sport_ids()

    if not sport_ids:
        print("No sport IDs found.")
        return
    
    for sport in sport_ids:
        sport_id = sport['sportID']
        
        # 使用 get_sport_name 函數獲取 sport_name
        sport_name = get_sport_name(sport_id)
        
        if not sport_name:
            print(f"Skipping sport ID {sport_id} due to missing sport name.")
            continue

        news_list = fetch_news(sport_name)

        print(f"Fetched {len(news_list)} news articles")

        for news in news_list:
            title = news.get("title", "No Title").replace('\xa0', ' ')
            description = news.get("description", "No description").replace('\xa0', ' ')
            news_date = news.get("publishedAt", "No Date").replace('\xa0', ' ')  # 更新日期欄位
            news_url = news.get("url", "No URL").replace('\xa0', ' ')  # 更新 URL 欄位
            source_id = news.get("source", {}).get("name", "Unknown").replace('\xa0', ' ')  # 提取 source id
            
            # 打印新聞細節
            print(f"Title: {title}")
            print(f"description: {description}")
            print(f"Date: {news_date}")
            print(f"Source ID: {source_id}")
            print(f"URL: {news_url}")
            print("-" * 50)

            # 使用 Gemini AI 或關鍵字進行判斷
            #response = gemini_response(description, title, sport_name)
                
            #if (response == "非股市新聞"):
            if sport_name not in news and sport_name not in title:
                print(f'非股市新聞:內文({description})標題:({title})')
                continue

            # 插入新聞，如果不存在相同的記錄
            insert_news_if_not_exists(sport_id, title, news_date, description, source_id, news_url)


if __name__ == "__main__":
    pages=int(sys.argv[1])
    main()
    print(get_all_sport_ids())
