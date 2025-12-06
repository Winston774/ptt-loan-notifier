# PTT 借貸版爬蟲 + LINE Bot 通知系統

自動監控 PTT 借貸版，篩選「信貸」相關文章，透過 LINE Bot 推播通知。

## 功能特色

- 🔍 **智慧監控**: 每分鐘自動抓取 PTT 借貸版
- 🏷️ **關鍵字過濾**: 篩選含「信貸」或「個人信貸」的文章
- 📱 **LINE 推播**: 透過 LINE Bot 即時通知
- 👥 **會員分級**:
  - **Premium**: 即時推播
  - **Standard**: 每小時批次通知
- 🗄️ **資料保存**: 完整文章內容存入資料庫，6個月後自動清理

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

複製 `.env.example` 為 `.env` 並填入實際值：

```bash
cp .env.example .env
```

主要設定項目：
- `DATABASE_URL`: PostgreSQL 連線字串
- `LINE_CHANNEL_TOKEN`: LINE Bot Channel Access Token
- `LINE_CHANNEL_SECRET`: LINE Bot Channel Secret

### 3. 本地執行

```bash
python main.py
```

服務啟動後可訪問:
- API 文件: http://localhost:8000/docs
- 健康檢查: http://localhost:8000/health

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/health` | 健康檢查 |
| POST | `/trigger` | 手動觸發爬蟲 |
| POST | `/trigger/hourly` | 手動觸發通知 |
| GET | `/jobs` | 列出排程任務 |
| POST | `/users` | 新增用戶 |
| PUT | `/users/{id}/tier` | 更新用戶等級 |
| GET | `/stats` | 系統統計 |

## 部署到 Zeabur

1. 在 Zeabur 建立新專案
2. 連接 GitHub 倉庫
3. 新增 PostgreSQL 服務
4. 設定環境變數
5. 部署完成！

## 專案結構

```
PTT/
├── main.py              # FastAPI 入口
├── config.py            # 環境設定
├── crawler/             # 爬蟲模組
│   ├── ptt_scraper.py   # PTT 爬蟲
│   └── parser.py        # HTML 解析
├── database/            # 資料庫模組
│   ├── models.py        # SQLAlchemy 模型
│   └── crud.py          # CRUD 操作
├── notification/        # 通知模組
│   └── line_bot.py      # LINE Bot
└── scheduler/           # 排程模組
    └── jobs.py          # 排程任務
```

## 授權

MIT License
