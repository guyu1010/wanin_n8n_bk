# Microsoft Teams 通知設定指南

## 問題說明

目前的 webhook URL 是 Power Automate 手動觸發器，不適合用於 HTTP 請求。需要重新建立。

## 解決方案（二選一）

---

### 方案 A：使用 Power Automate + Adaptive Card（推薦，卡片最漂亮）

#### 步驟 1：建立 Power Automate Flow

1. 前往 [Power Automate](https://make.powerautomate.com/)
2. 建立新的「自動化雲端流程」
3. 觸發器選擇：**「When a HTTP request is received」**（重要！）
4. 儲存後會產生 HTTP POST URL，複製此 URL

#### 步驟 2：設定 Request Body JSON Schema

在觸發器中，點擊「使用範例承載來產生結構描述」，貼上：

```json
{
  "title": "n8n 工作流程備份完成",
  "status": "success",
  "timestamp": "2025-11-05 14:30:25",
  "n8n_url": "http://103.130.125.54:5678",
  "type": "backup",
  "total_count": 15,
  "changed_count": 3,
  "changed_workflows": ["工作流程1", "工作流程2"],
  "github_url": "https://github.com/guyu1010/wanin_n8n_bk_data",
  "health_status": "healthy",
  "error": ""
}
```

#### 步驟 3：新增動作 - 張貼 Adaptive Card

1. 點擊「新增步驟」
2. 搜尋「Post adaptive card in a chat or channel」
3. 選擇你的 Teams 和頻道
4. 在 Adaptive Card 區域貼上以下 JSON：

**備份完成卡片**（使用條件：當 `type` = `backup`）：

```json
{
  "type": "AdaptiveCard",
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "version": "1.4",
  "body": [
    {
      "type": "TextBlock",
      "text": "✅ @{triggerBody()?['title']}",
      "size": "Large",
      "weight": "Bolder",
      "color": "Good"
    },
    {
      "type": "FactSet",
      "facts": [
        {
          "title": "⏰ 備份時間",
          "value": "@{triggerBody()?['timestamp']}"
        },
        {
          "title": "📊 總流程數",
          "value": "@{triggerBody()?['total_count']}"
        },
        {
          "title": "✏️ 本次變更",
          "value": "@{triggerBody()?['changed_count']}"
        }
      ]
    },
    {
      "type": "TextBlock",
      "text": "**變更的工作流程：**",
      "weight": "Bolder",
      "spacing": "Medium"
    },
    {
      "type": "TextBlock",
      "text": "@{join(triggerBody()?['changed_workflows'], '\n• ')}",
      "spacing": "Small"
    }
  ],
  "actions": [
    {
      "type": "Action.OpenUrl",
      "title": "開啟 n8n",
      "url": "@{triggerBody()?['n8n_url']}"
    },
    {
      "type": "Action.OpenUrl",
      "title": "查看備份",
      "url": "@{triggerBody()?['github_url']}"
    }
  ]
}
```

**服務異常卡片**（使用條件：當 `type` = `health` 且 `status` = `error`）：

```json
{
  "type": "AdaptiveCard",
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "version": "1.4",
  "body": [
    {
      "type": "TextBlock",
      "text": "⚠️ @{triggerBody()?['title']}",
      "size": "Large",
      "weight": "Bolder",
      "color": "Attention"
    },
    {
      "type": "FactSet",
      "facts": [
        {
          "title": "⏰ 時間",
          "value": "@{triggerBody()?['timestamp']}"
        },
        {
          "title": "📍 狀態",
          "value": "@{triggerBody()?['health_status']}"
        }
      ]
    },
    {
      "type": "TextBlock",
      "text": "**錯誤訊息：**",
      "weight": "Bolder",
      "spacing": "Medium"
    },
    {
      "type": "TextBlock",
      "text": "@{triggerBody()?['error']}",
      "color": "Attention",
      "wrap": true
    }
  ],
  "actions": [
    {
      "type": "Action.OpenUrl",
      "title": "檢查 n8n",
      "url": "@{triggerBody()?['n8n_url']}"
    }
  ]
}
```

#### 步驟 4：更新 config.json

將新的 HTTP POST URL 更新到 config.json：

```json
{
  "notifications": {
    "webhook": {
      "enabled": true,
      "platform": "teams",
      "url": "你的新 HTTP POST URL"
    }
  }
}
```

---

### 方案 B：使用傳統 Teams Incoming Webhook（較簡單但功能少）

#### 步驟 1：建立 Incoming Webhook

1. 前往你的 Teams 頻道
2. 點擊頻道名稱旁的「...」→ 「連接器」
3. 搜尋「Incoming Webhook」→ 「設定」
4. 輸入名稱（例如：n8n 監控）
5. 複製 Webhook URL

#### 步驟 2：修改程式碼

需要調整程式碼以支援傳統 Teams webhook 格式。

在 `config.json` 中：

```json
{
  "notifications": {
    "webhook": {
      "enabled": true,
      "platform": "teams_connector",  // 注意這裡改成 teams_connector
      "url": "你的 Incoming Webhook URL"
    }
  }
}
```

---

## 建議

**強烈推薦使用方案 A**，原因：
- ✅ Adaptive Card 外觀更專業
- ✅ 支援按鈕動作（直接點擊開啟 n8n）
- ✅ 可以在 Flow 中加入更多邏輯（例如：只在工作時間通知、通知特定人員等）
- ✅ 更靈活的格式化選項

---

## 測試

設定完成後，執行測試腳本：

```bash
python3 test_teams_notification.py
```

如果成功，你會在 Teams 頻道看到 3 張卡片通知。

---

## 常見問題

### Q: 仍然收到 403 錯誤？
A: 確認你使用的是「When a HTTP request is received」觸發器，不是「手動觸發器」。

### Q: 卡片沒有正確顯示工作流程列表？
A: 檢查 Power Automate 中 Adaptive Card 的語法，特別是 `@{join(...)}` 部分。

### Q: 想要客製化卡片外觀？
A: 可以使用 [Adaptive Cards Designer](https://adaptivecards.io/designer/) 設計你的卡片。

---

## 下一步

設定完成後，你可以：
1. 設定 cron job 定期執行備份
2. 調整通知頻率和條件
3. 新增更多通知管道（Email、Slack 等）
