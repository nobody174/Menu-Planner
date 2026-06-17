# Pi-Menu Shopping List Integrations

Complete guide for setting up shopping list integrations with various services.

## Quick Start

1. Click the **📤 Export & Sync** button on the shopping list page
2. Choose your integration or export format
3. Configure API keys (if required) in your `.env` file
4. Click to export/sync

## Export Formats

All formats are available without any configuration:

### CSV
- Spreadsheet-compatible format
- Columns: Category, Ingredient, Quantity, Unit
- Perfect for Excel/Google Sheets

### JSON
- Machine-readable format
- Includes metadata (export timestamp)
- Great for data analysis

### Plain Text
- Human-readable format with emojis
- Organized by category
- Easy to share

### ICS (iCalendar)
- Apple Reminders compatible
- Each item becomes a reminder
- Download and open with Reminders app

### Copy to Clipboard
- Quick copy for pasting elsewhere
- Formatted as plain text
- No file download needed

## Task Manager Integrations

### Microsoft To Do ✅ (Built-in)

**Setup:**
1. Click "Microsoft To Do" button
2. Sign in when prompted (first time only)
3. Items sync to "Pi-Menu Handleliste" list

**Configuration:**
- No API key needed
- Uses OAuth authentication
- Token stored locally

**Features:**
- Automatic list creation
- Category-aware tasks
- Smart emoji icons per ingredient

---

### Todoist ✅ (API Available)

**Setup:**
1. Get API token: https://todoist.com/app/settings/integrations/developer
2. Add to `.env` file:
   ```
   TODOIST_API_TOKEN=your_token_here
   ```
3. Click "Todoist" button on shopping list

**Configuration:**
- Find your API token in: Settings → Integrations → Developer
- Token never expires but can be regenerated

**Features:**
- Creates project: "Pi-Menu Shopping"
- Items get category labels
- Supports priorities and due dates

---

### TickTick ✅ (API Available)

**Setup:**
1. Get API token: https://ticktick.com/user/myprofile
2. Add to `.env` file:
   ```
   TICKTICK_API_TOKEN=your_token_here
   ```
3. Click "TickTick" button on shopping list

**Configuration:**
- API token found in user settings
- Can revoke/regenerate anytime

**Features:**
- Creates list: "Pi-Menu Shopping"
- Items tagged by category
- Syncs across all devices

---

### Any.do ✅ (API Available)

**Setup:**
1. Get API token: https://www.any.do/en/settings/account
2. Add to `.env` file:
   ```
   ANYDO_API_TOKEN=your_token_here
   ```
3. Click "Any.do" button on shopping list

**Configuration:**
- Generate token in account settings
- Secure token storage required

**Features:**
- Creates "Pi-Menu Shopping" list
- Category-based organization
- Full cross-device sync

---

## Note Taking & Other Services

### Google Keep 📝 (Email Workaround)

**Setup:**
1. Identify your Google Keep email (check email forwarding)
2. Add to `.env` file:
   ```
   GOOGLE_KEEP_EMAIL=your-keep-email@google.com
   ```
3. Click "Google Keep" button

**Configuration:**
- Optional SMTP for automatic emails
- Or manually send the text file to your Keep address
- Keep auto-imports emails

**Features:**
- Color-coded by category
- Voice notes support
- Mobile app integration

---

### Notion ✅ (API Available)

**Setup:**
1. Create integration: https://www.notion.so/my-integrations
2. Create a database with these properties:
   - Name (text)
   - Category (select)
   - Ingredient (text)
   - Quantity (number)
   - Unit (text)
3. Share database with integration
4. Add to `.env` file:
   ```
   NOTION_API_TOKEN=your_token_here
   NOTION_DATABASE_ID=your_database_id
   ```
5. Click "Notion" button on shopping list

**Configuration:**
- Create free Notion workspace
- Integration requires Notion account
- Database ID found in share/copy URL

**Features:**
- Fully customizable database
- Rich formatting support
- Real-time sync
- Can be embedded anywhere

---

### Trello ✅ (API Available)

**Setup:**
1. Get API key: https://trello.com/app-key
2. Generate token on the same page
3. Add to `.env` file:
   ```
   TRELLO_API_KEY=your_key_here
   TRELLO_API_TOKEN=your_token_here
   ```
4. Click "Trello" button on shopping list

**Configuration:**
- API key available immediately
- Token generated with one click
- Never commit these to version control

**Features:**
- Creates board: "Pi-Menu Shopping"
- Lists per category
- Items as cards
- Drag-and-drop organization

---

### Apple Reminders 📅 (ICS Export)

**Setup:**
1. Click "Apple Reminders" button
2. Download ICS file
3. Open with Reminders app or double-click
4. Choose which list to add to

**Configuration:**
- No API token needed
- Works on any Apple device
- Auto-syncs via iCloud

**Features:**
- Category awareness
- Emoji icons per item
- Native iOS/macOS integration
- Voice control support

---

## .env Configuration Template

```bash
# Microsoft To Do (optional - uses OAuth flow)
# No API key needed, uses login flow

# Todoist
TODOIST_API_TOKEN=your_token_here

# TickTick
TICKTICK_API_TOKEN=your_token_here

# Any.do
ANYDO_API_TOKEN=your_token_here

# Trello
TRELLO_API_KEY=your_key_here
TRELLO_API_TOKEN=your_token_here

# Notion
NOTION_API_TOKEN=your_token_here
NOTION_DATABASE_ID=your_database_id

# Google Keep (optional)
GOOGLE_KEEP_EMAIL=your-keep-email@google.com
```

## Troubleshooting

### "Configuration needed" error
- Check that API token is set in `.env`
- Restart Flask after changing `.env`
- Verify token is correct and has correct permissions

### Sync fails with "401 Unauthorized"
- Token may have expired
- Check if service requires re-authentication
- Generate a new token if needed

### Items appear but with wrong formatting
- Check if service requires specific field formats
- Some services have character limits
- Try exporting as CSV/JSON first to debug

### No items appear in list
- Ensure items are unchecked (checked items are filtered out)
- Try with just a few items first
- Check service's app for errors

## Bilingual Support

All integrations work in both English and Norwegian:

- UI text automatically translates based on language setting
- Shopping list content uses selected language
- Category names translated in export/sync
- Emoji icons are language-neutral

## Security Notes

⚠️ **Important:**
- Never commit `.env` file to git
- Keep API tokens private
- Tokens stored locally only
- Each service can revoke tokens anytime
- No passwords stored (token-based auth only)

## API Limits

Most services have rate limits:
- **Todoist**: 350 requests/min
- **TickTick**: 1,000 requests/day
- **Trello**: 300 requests/sec per token
- **Notion**: 3 requests/sec
- **Any.do**: varies by plan

Normal usage won't exceed these limits.

## Coming Soon

- Omnifocus integration
- Microsoft Lists
- Jira Tasks
- GitHub Issues as shopping list
- Slack message export
- Webhook support for custom apps

## Support

For issues or feature requests, visit:
https://github.com/nobody174/Pi-Menu-Public/issues
