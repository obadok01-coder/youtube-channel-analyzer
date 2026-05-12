# Make.com Scenario Setup Instructions
# YouTube Channel Analyzer - Automation Flow

## Scenario Name: "YouTube Channel Outlier Analyzer"

## Step 1: Trigger - Watch Google Sheets
Module: Google Sheets > Watch New Rows
- Connection: Your Google account
- Sheet: Create a Google Sheet with columns:
  | URL |
  |-----|
  | https://youtube.com/@ChannelName |
- Limit: 1 row at a time

## Step 2: Action - Send to Analysis API
Module: HTTP > Make a Request
- URL: https://YOUR-VERCEL-APP.vercel.app/api/analyze
- Method: POST
- Headers:
  Content-Type: application/json
- Body type: Raw
- Body content:
  {
    "url": "{{1.URL}}"
  }
  (Map from Google Sheets "URL" column)

## Step 3: Parse Response
Module: JSON > Parse JSON
- JSON string: {{2.data}}  (from HTTP module output)

## Step 4: Send Telegram Alert (Optional)
Module: Telegram Bot > Send a Message
- Chat ID: Your chat/group ID
- Text:
  Channel: {{3.channel_name}}
  Outliers Found: {{length(3.outliers)}}
  {{#each 3.outliers}}
  - {{title}} ({{ratio}}x avg)
  {{/each}}

## Step 5: Update Google Sheets with Results (Optional)
Module: Google Sheets > Update a Row
- Spreadsheet ID: Same sheet
- Update cells with: outlier count, top video title, top ratio

## JSON Response Structure from API
{
  "status": "success",
  "channel_name": "...",
  "total_videos_analyzed": 50,
  "average_views": 5000000,
  "outliers": [
    {
      "title": "...",
      "link": "https://youtube.com/watch?v=...",
      "thumbnail": "...",
      "views": 25000000,
      "avg_views": 5000000,
      "ratio": 5.0,
      "title_analysis": "...",
      "transcript_analysis": "..."
    }
  ]
}

## Webhook Alternative
Instead of Google Sheets trigger, use:
Module: Webhook > Custom Webhook
- This gives you a unique webhook URL
- POST to it with {"url": "channel_url"}
- Then use the same HTTP + Telegram pipeline
