# Make.com Scenario Setup

## Quick Start
The backend is ready at: `POST https://youtube-analyzer-red.vercel.app/api/make-webhook`

## Endpoints

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `POST /api/make-webhook` | Token required | Make.com optimized webhook with flattened fields |
| `POST /api/analyze` | None | Manual analysis via frontend |
| `GET /api/health` | None | Health check |

## Make.com Webhook Auth
Header: `Authorization: Token LNhHBIzStIl1UPqbA4oDiXu9E2MQOsK6aeon3EE0Ft`

## Flattened Response Fields (easy Make.com mapping)
```
channel_name       -> Text
total_videos       -> Number
average_views      -> Number
outlier_count      -> Number
top_outlier_title  -> Text
top_outlier_ratio  -> Number
top_outlier_views  -> Number
top_outlier_link   -> URL
top_title_analysis -> Text
top_transcript_analysis -> Text
outliers[]         -> Array (title, link, ratio, ai_analysis)
```

## Scenario Setup in Make.com

### Step 1: Google Sheets Trigger
- Module: Google Sheets > Watch New Rows
- Spreadsheet: Create sheet with column "URL"
- Add channel URLs like: https://youtube.com/@MrBeast

### Step 2: HTTP Request
- Module: HTTP > Make a Request
- URL: https://youtube-analyzer-red.vercel.app/api/make-webhook
- Method: POST
- Headers:
  - Content-Type: application/json
  - Authorization: Token LNhHBIzStIl1UPqbA4oDiXu9E2MQOsK6aeon3EE0Ft
- Body: { "url": "{{1.URL}}" }

### Step 3: Parse JSON
- Module: JSON > Parse JSON
- JSON string: {{2.data}}

### Step 4: Telegram Alert
- Module: Telegram Bot > Send a Message
- Chat ID: Your chat/group ID
- Text:
  Channel: {{3.channel_name}}
  Avg Views: {{3.average_views}}
  Outliers: {{3.outlier_count}}
  Top: {{3.top_outlier_title}} ({{3.top_outlier_ratio}}x)
  Link: {{3.top_outlier_link}}

## Alternative: Webhook Trigger
Make.com also provides a custom webhook URL you can use instead of Google Sheets:
- Module: Webhook > Custom Webhook
- Copy the generated URL
- POST to it with: {"url": "https://youtube.com/@Channel"}
- Chain to HTTP module above
