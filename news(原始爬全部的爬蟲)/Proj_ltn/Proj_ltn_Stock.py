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
import requests
import asyncio
from datetime import datetime, timedelta
import google.generativeai as genai
from langchain.schema.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from google.generativeai.types import HarmBlockThreshold
from google.ai.generativelanguage_v1 import HarmCategory
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
import re #new

# 常見的 User-Agent 列表
user_agents = [ 
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.70 Safari/537.36"  # 新增的 user-agent
]

# 加載環境變量
load_dotenv()

# Supabase 配置
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_stock_name(stock_id):
    """從suapabase抓股票名稱"""
    try:
        response = supabase.table('stock').select('stock_name').eq('stockID', stock_id).execute()
        if not response.data:
            print(f"No stock name found for stock ID: {stock_id}")
            return None
        return response.data[0]['stock_name']
    except Exception as e:
        print(f"Error fetching stock name for {stock_id}: {e}")
        return None

def fetch_news_ltn(stock_id, stock_name, start_page, end_page):
    """從 ltn 獲取指定範圍的新聞"""
    keyword = stock_name
    encoded_keyword = quote(keyword)
    today_date = datetime.now().strftime("%Y%m%d")
    base_url = f"https://search.ltn.com.tw/list?keyword={encoded_keyword}&start_time=20041201&end_time={today_date}&sort=date&type=all&page="

    news_url_list = []

    # 創建 WebDriver 實例
    driver = webdriver.Chrome()

    for page in range(start_page, end_page + 1):
        url = base_url + str(page)
        driver.get(url)
        
        try:
            # 使用顯示等待，等待特定元素出現
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "cont") or contains(@class, "article")]'))
            )
            
            # 嘗試多個XPATH找到新聞連結
            elements = driver.find_elements(By.XPATH, '//div[contains(@class, "cont") or contains(@class, "article")]/a')
            
            if len(elements) < 10:
                print(f"{keyword} - 頁面內容不足，停止爬蟲...")
                break
            
            # 初始化一個集合來儲存已添加的網址
            seen_hrefs = set()
            
            for e in elements:
                href = e.get_attribute('href')
                if href and href not in seen_hrefs:
                    print(f"{keyword} - 目標元素的網址:", href)
                    news_url_list.append(href)
                    seen_hrefs.add(href)    # 將 href 加入集合，避免重複
                    
        except TimeoutException:
            print(f"{keyword} - 網頁載入超時，重新載入...")
            continue
        
        # 延時避免過快請求
        time.sleep(1)
    
    driver.quit()   # 關閉 WebDriver 實例
    
    # 找到所有自由財經的網址
    news_url_list = [href for href in news_url_list if href.startswith("https://ec")]

    # 爬取詳細新聞内容並存到 Supabase
    news_list = []
    for index, link in enumerate(news_url_list):
        try:
            response = requests.get(link)
            soup = BeautifulSoup(response.content, 'html.parser')

            formatted_date = "Unknown Date"  # 預設值以防錯誤
            
            # 嘗試使用正則表達式抓取時間
            time_element = soup.find_all('span', class_='time')
            if time_element and len(time_element) > 1:
                time_text = time_element[1].text.strip()
                date_match = re.search(r'\d{4}/\d{2}/\d{2}', time_text)
                if date_match:
                    formatted_date = datetime.strptime(date_match.group(), '%Y/%m/%d').strftime('%Y-%m-%d')
                else:
                    print(f"{keyword} - 日期格式錯誤: {time_text}, 使用預設日期.")
            
            # 提取文章內容
            article = ''
            content_div = soup.find_all('div', class_="text")
            if content_div and len(content_div) > 1:
                contents = content_div[1].find_all('p')[:-2]
                for content in contents:
                    article += content.text.strip()
            
            news_list.append({
                "headline": soup.find('h1').text.strip() if soup.find('h1') else "No Headline",
                "link": link,
                "date": formatted_date,
                "content": article
            })
            
            print(f'[{index+1}/{len(news_url_list)}], {keyword} - Date:{formatted_date}, headline:{soup.find("h1").text.strip() if soup.find("h1") else "No Headline"}, link:{link}')

        except Exception as e:
            print(f"{keyword} - 爬取失敗: {e}")
            print(f'[{index+1}/{len(news_url_list)}], {keyword} - Date:{formatted_date}, link:{link}')
            continue
        
        time.sleep(1)
    
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
def gemini_response(news, title):
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
    
    # 替代方案：直接判斷新聞內容是否包含股票名稱
    if not ((stock_name in news) or (stock_name in title)):
        print(f'非股市新聞:內文({news})標題:({title})')
        return "非股市新聞"

    return "股市新聞"  # 如果新聞相關，返回相應的結果

# 從 Supabase 中獲取所有股票的 stockID
stocks_response = supabase.table("stock").select("stockID").execute()

# 確認是否拿到資料
if not stocks_response or not stocks_response.data:
    print(f"Error fetching stock IDs: {stocks_response}")
    exit()

stock_ids = stocks_response.data  # 獲取 stockID 資料


# 循環，控制總爬取頁數
for current_page in range(1, 1501, 3):  # 每次迭代爬取3页
    print(f'current page: {current_page}')
    for stock in stock_ids:
        stock_id = stock['stockID']
        
        # 使用 get_stock_name 函數獲取 stock_name
        stock_name = get_stock_name(stock_id)
        
        if not stock_name:
            print(f"Skipping stock ID {stock_id} due to missing stock name.")
            continue

        end_page = min(current_page + 2, 1500)  # 設定結束頁面為當前頁的3頁之後或1500

        # 爬取新聞（包括標題、連結、日期和內容）
        news_list = fetch_news_ltn(stock_id, stock_name, current_page, end_page)
        
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
                    "source": "ltn",
                    "url": news["link"]
                }).execute()
                print(f"Saved news: {news['headline']} for stock ID: {stock_id} on date: {news['date']}")
                
            except Exception as e:
                print(f"Error processing news for stock ID {stock_id}: {e}")  

