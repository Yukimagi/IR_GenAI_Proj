# IR_GenAI Project

## Set Up
To set up the project, follow these steps:
1. Install the required Python packages:
    ```sh
    pip install -r requirements.txt
    ```
2. Create a要放入所有Proj_*資料夾中 `.env` file (env1內的.env為資料庫1，2則為資料庫2，你可以替換.env成你需要的資料庫)
3. Store `GEMINI_API_KEY='your api key'` in it.(please get api here:https://ai.google.dev/)
4. Store `NEWS_API_KEY='your api key'` in it.(please get api here: https://newsapi.org/)
5. Store `SUPABASE_URL=https://pwwpdkqppibpltojdsgu.supabase.co'` in it.
6. Store `SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB3d3Bka3FwcGlicGx0b2pkc2d1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMDIwMjI3OSwiZXhwIjoyMDQ1Nzc4Mjc5fQ.MX3vok9ZIAwfV4kBzktfM5090Z9qtMSmdo6K2NGhPHI'` in it.
7. Compile `app.py` to start the server for training and testing.

## Website Introduction
- **index.html**: Serves as the homepage.
- **about.html**: Provides an introduction to this project and its contributors.
- **crawl.html**: Helps you fetch the necessary data. (Please retrieve data daily.)
- **emotion.html**: Let you get sentiment visualization(dynamic).

## About Database
- 請參考word中的資料庫介紹
- 請在此資料夾查看"CSV資料庫"以csv存個個資料表，並分別存DB1和DB2的資料庫內容。
- 請在此資料夾查看"sql資料庫"以sql存個個資料表，並分別存DB1和DB2的資料庫內容。

## About Original Program(about sentiment and crawler)
- crawl請參考"news(原始爬全部的爬蟲)"
- 產生sentiment score請參考"sentiment"

## Questions?
If you have any questions, please contact one of the contributors.
