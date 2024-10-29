from supabase import create_client, Client
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

# 常見的 User-Agent 列表(這是一種adaptive)
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1"
]

# 加載環境變量
load_dotenv()

# Supabase 設定
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_stock_name(stock_id):
    """從 Supabase 獲取股票名稱"""
    try:
        response = supabase.table('stock').select('stock_name').eq('stockID', stock_id).execute()
        if not response.data:
            print(f"No stock name found for stock ID: {stock_id}")
            return None
        return response.data[0]['stock_name']
    except Exception as e:
        print(f"Error fetching stock name for {stock_id}: {e}")
        return None

def safe_find_element(driver, selectors):
    """嘗試多組選擇器定位元素"""
    for selector in selectors:
        try:
            return driver.find_element(*selector)
        except:
            continue
    return None  # 若全部失敗返回 None

def fetch_news_chinatime(stock_id, stock_name, start_page, end_page):
    """從 Chinatime 獲取指定範圍的新聞"""
    keyword = f'{stock_name}'
    encoded_keyword = quote(keyword)
    base_url = f"https://www.chinatimes.com/search/{encoded_keyword}?page="

    news_list = []
    
    for i in range(start_page, end_page + 1):  # 爬取指定範圍的頁面
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        random_user_agent = random.choice(user_agents)
        options.add_argument(f"user-agent={random_user_agent}")

        driver = webdriver.Chrome(options=options)

        # 隱藏 webdriver 特徵
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })

        try:
            url = base_url + str(i) + "&chdtv"
            driver.get(url)

            # 隨機延遲
            time.sleep(random.uniform(1, 3))

            # 增加錯誤重試機制
            retries = 3
            while retries > 0:
                try:
                    WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "article-list"))
                    )
                    break  # 成功時退出循環
                except Exception:
                    retries -= 1
                    if retries == 0:
                        print("Failed to load page after retries.")
                        break

            # 提取文章列表
            articles = driver.find_elements(By.CSS_SELECTOR, ".article-list li")

            for article in articles:
                try:
                    title_element = safe_find_element(article, [(By.TAG_NAME, "h3"), (By.CSS_SELECTOR, ".title")])
                    link_element = safe_find_element(article, [(By.TAG_NAME, "a")])
                    time_element = safe_find_element(article, [(By.TAG_NAME, "time")])
                    intro_element = safe_find_element(article, [(By.CLASS_NAME, "intro"), (By.CSS_SELECTOR, ".summary")])

                    if title_element and link_element and time_element and intro_element:
                        title_text = title_element.text
                        link_url = link_element.get_attribute("href")
                        time_text = time_element.get_attribute("datetime")
                        intro_text = intro_element.text

                        time_datetime = datetime.strptime(time_text, "%Y-%m-%d %H:%M")
                        news_date = time_datetime.strftime("%Y-%m-%d")

                        news_list.append({
                            "headline": title_text,
                            "link": link_url,
                            "date": news_date,
                            "content": intro_text
                        })

                        print(f"Fetched: {title_text}, Link: {link_url}")

                except Exception as e:
                    print(f"Error extracting article on page {i}: {e}")

        except Exception as e:
            print(f"Error accessing Chinatime: {e}")
        finally:
            driver.quit()  # 關閉瀏覽器

    return news_list

def check_news_count(stock_id, news_date):
    """檢查特定日期是否已儲存3則新聞"""
    try:
        response = supabase.table('stock_news_test').select('id').eq('stockID', stock_id).eq('date', news_date).execute()
        if response.data:
            return len(response.data)  # 返回已儲存的新聞數量
        return 0
    except Exception as e:
        print(f"Error checking news count for {stock_id} on {news_date}: {e}")
        return 0
test=0 
def gemini_response(news, title):
    global test  # 指示使用全域變數
    model = 'gemini-1.5-flash'
    temperature = 1
    top_p = 0.9
    seed = 0
    load_dotenv()

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
    以下是今天的新聞資訊。請根據這些資訊判斷其是否是股市新聞，如果不是請回答無關：

    標題:
    {title}

    文章內容:
    {news}
    """
    if test==0:
        try:
            response = llm.invoke(prompt)
            response_content = response.content
            print(response_content.strip())
            # 先檢查 API 的回應
            if "無關" in response_content:
                print(f'非股市新聞:內文({news})標題:({title})')
                return "非股市新聞"
        except Exception as e:
            print(e)
            # API 不可用的情況下直接進行替代判斷
            print("API不可用，進行替代方案判斷")
            test=1
    
    # 替代方案：直接判斷新聞內容是否包含股票名稱
    if not ((stock_name in news) or (stock_name in title)):
        print(f'非股市新聞:內文({news})標題:({title})')
        return "非股市新聞"

    return "股市新聞"  # 如果新聞相關，返回相應的結果

# 从 Supabase 中获取所有股票的 stockID
stocks_response = supabase.table("stock").select("stockID").execute()

# 確認是否拿到資料
if not stocks_response or not stocks_response.data:
    print(f"Error fetching stock IDs: {stocks_response}")
    exit()

stock_ids = stocks_response.data  # 获取 stockID 数据

# 循环，控制总爬取的页数
for current_page in range(1, 1501, 3):  # 每次迭代爬取3页
    print(f'current page: {current_page}')
    for stock in stock_ids:
        stock_id = stock['stockID']
        
        # 使用 get_stock_name 函数获取 stock_name
        stock_name = get_stock_name(stock_id)
        
        if not stock_name:
            print(f"Skipping stock ID {stock_id} due to missing stock name.")
            continue

        end_page = min(current_page + 2, 1500)  # 設定結束頁面為當前頁的3頁之後或1500

        # 爬取新聞（包括標題、連結、日期和內容）
        news_list = fetch_news_chinatime(stock_id, stock_name, current_page, end_page)
        
        for news in news_list:
            try:
                news_date = news["date"]
                
                # 檢查該日期是否已儲存3則新聞
                if check_news_count(stock_id, news_date) >= 3:
                    print(f"Already saved 3 news articles for {stock_id} on {news_date}. Skipping...")
                    continue
                
                response = gemini_response(news["content"], news["headline"])
                
                if response == "非股市新聞":
                    print(f'非股市新聞:內文({news["content"]})標題:({news["headline"]})')
                    continue
                
                # 儲存到 Supabase
                supabase.table("stock_news_test").insert({
                    "stockID": int(stock_id),
                    "title": news["headline"],
                    "date": news["date"],
                    "content": news["content"],
                    "source": "China Times",
                    "url": news["link"]
                }).execute()
                print(f"Saved news: {news['headline']} for stock ID: {stock_id} on date: {news['date']}")
                
            except Exception as e:
                print(f"Error processing news for stock ID {stock_id}: {e}")
