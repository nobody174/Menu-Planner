# Pi-Menu Shopping List Integration Setup Guide

Complete step-by-step instructions for syncing your shopping list to various task managers and export formats.

---

## 📋 Table of Contents

1. [Export Formats](#export-formats) - CSV, JSON, Text, ICS
2. [Todoist](#todoist) - Popular task manager
3. [TickTick](#ticktick) - Powerful task management
4. [Apple Reminders](#apple-reminders) - Native iOS/macOS

---

## Export Formats

### 💾 Available Formats

All of these can be downloaded directly from the "Export & Sync" menu:

- **CSV** - Spreadsheet format (Excel, Google Sheets)
- **JSON** - Data format for integration with other tools
- **Text** - Plain text format (easy to read and share)
- **ICS** - Calendar format (Apple Calendar, Google Calendar, etc.)
- **Clipboard** - Copy directly to paste anywhere

### 📝 How to Use

1. Go to Pi-Menu **Shopping List** page
2. **Uncheck items** you want to export (checked items are ignored)
3. Click **"📤 Export & Sync"** button
4. Select your desired format
5. File downloads or text is copied to clipboard

### ✅ All Formats Fully Supported

No setup needed - just select and download!

---

## Todoist

### ✅ What You Need
- A Todoist account (free or paid)
- Your API token (2-minute setup)

### 🔗 Helpful Links
- **Sign up/Login:** https://todoist.com/app/today
- **Get API token:** https://app.todoist.com/app/settings/integrations/developer
- **View your tasks:** https://todoist.com/app/today

### 📝 Step-by-Step Setup

#### Step 1: Create a Todoist Account
1. Go to https://todoist.com/app/today
2. Click **"Sign up"** (or sign in if you already have an account)
3. Enter your email and password
4. Verify your email
5. Done! You now have a Todoist account

#### Step 2: Get Your API Token
1. Go to https://app.todoist.com/app/settings/integrations/developer
2. Under **"API token"** section, you'll see your token (long string of characters)
3. **Copy** this token
4. Keep it safe - don't share it!

#### Step 3: Add Token to Pi-Menu
1. Find your `.env` file (in the Pi-Menu main folder)
   - If you don't have one, copy `.env.template` and rename to `.env`
2. Find this line:
   ```
   TODOIST_API_TOKEN=
   ```
3. Paste your token after the `=` sign:
   ```
   TODOIST_API_TOKEN=abc123xyz789...
   ```
4. Save the file
5. **Restart Flask** (stop and start the Flask server)

#### Step 4: Test It
1. Go to Pi-Menu shopping list
2. Uncheck the items you want to sync
3. Click "📤 Export & Sync" button
4. Click "🔶 Todoist"
5. Wait for the "Syncing..." message to complete
6. Items appear in your Todoist account

**Important:** The first sync creates the "Pi-Menu Shopping" project. Syncing again will update the same project and replace old items with new ones.

### 📱 View Your Items
1. Open https://todoist.com/app/today
2. Find the **"Pi-Menu Shopping"** project
3. All your items will be listed there with category labels

### 🔄 Sync Multiple Times
- Just click the button again whenever you want to update
- Items are updated, not duplicated

### ❓ Troubleshooting
| Problem | Solution |
|---------|----------|
| "Configuration needed" error | Check `.env` file has correct token, restart Flask |
| Items not appearing in Todoist | Check the "Pi-Menu Shopping" project exists |
| Token not working | Generate a new one at https://app.todoist.com/app/settings/integrations/developer |
| 401 Unauthorized | Token is wrong or expired - get a new one |

---

## TickTick

### ✅ What You Need
- A TickTick account (free or paid)
- Your API token (3-minute setup)

### 🔗 Helpful Links
- **Sign up/Login:** https://ticktick.com
- **Get API token:** https://ticktick.com/webapp/#q/all/completed?modalType=settings
- **View your tasks:** https://ticktick.com

### 📝 Step-by-Step Setup

#### Step 1: Create a TickTick Account
1. Go to https://ticktick.com
2. Click **"Sign up"** (or sign in if you have an account)
3. Enter your email and password
4. Verify your email
5. Complete setup

#### Step 2: Get Your API Token
1. Go to https://ticktick.com/webapp/#q/all/completed?modalType=settings
2. Click your **profile name** in the top left
3. Click **"Settings"**
4. Click **"Account"** tab on the left
5. On the right side, find **"API Keys"** section
6. Click **"Manage"**
7. Click **"Enable Key"** button
8. Give it a name (e.g., "Shopping list")
9. Click **"Add"**
10. A window appears showing your API key
11. Click the **"Copy"** button next to the key
12. Keep it private!

#### Step 3: Add Token to Pi-Menu
1. Open your `.env` file (in the Pi-Menu main folder)
   - If missing, copy `.env.template` and rename to `.env`
2. Find this line:
   ```
   TICKTICK_API_TOKEN=
   ```
3. Paste your token:
   ```
   TICKTICK_API_TOKEN=your_token_here
   ```
4. Save the file
5. **Restart Flask**

#### Step 4: Test It
1. Go to Pi-Menu shopping list
2. Uncheck items you want to sync
3. Click "📤 Export & Sync"
4. Click "🎯 TickTick"
5. Items appear in TickTick under "Pi-Menu Shopping" list

### 📱 View Your Items
1. Open https://ticktick.com
2. Find **"Pi-Menu Shopping"** list on the left sidebar
3. All items are there with category tags

### ❓ Troubleshooting
| Problem | Solution |
|---------|----------|
| Can't find API token section | Check Settings → scroll to API Keys section |
| "Configuration needed" error | Verify token is correct in `.env`, restart Flask |
| Items not syncing | Try generating a new token |
| 404 Error | API token format incorrect - generate a new one |

---

## Apple Reminders

### ✅ What You Need
- An Apple device (iPhone, iPad, Mac) - or just download the file
- Nothing else! It's built-in.

### 🚀 Quick Start

#### Step 1: Export as ICS
1. Go to Pi-Menu shopping list
2. Uncheck items you want to export
3. Click "📤 Export & Sync"
4. Click "🍎 Apple Reminders"
5. File downloads to your computer

#### Step 2: Open with Reminders
1. **On Mac:** Double-click the `.ics` file → opens in Reminders
2. **On iPhone/iPad:**
   - Email yourself the `.ics` file
   - Open the email on your Apple device
   - Tap the attachment
   - Select "Add to Reminders"
   - Choose which list to add to

#### Step 3: Done!
- Items appear as reminders
- Syncs across all your Apple devices via iCloud

### 📱 View Your Items
1. Open **Reminders** app
2. Check your selected list
3. Items are there with emoji icons
4. Mark as complete when done

### 💡 Tips
- Create a dedicated "Shopping" list in Reminders for easy access
- Use Siri: "Add milk to Shopping list"
- Get notifications for your shopping list
- Share list with family members

### ❓ Troubleshooting
| Problem | Solution |
|---------|----------|
| File won't open | Make sure you have Reminders app installed |
| Items not syncing | Restart Reminders app and check iCloud sync |
| Multiple copies | Duplicate items can be merged in Reminders |

---

## 🔒 Security Best Practices

### Keeping Your Credentials Safe

✅ **DO:**
- Keep API tokens private
- Never share your `.env` file
- Regenerate tokens if they're leaked
- Use strong, unique passwords
- Only add integrations you'll actually use

❌ **DON'T:**
- Post tokens on GitHub or public forums
- Share screenshots with tokens visible
- Use the same token across multiple services
- Store tokens in plain text notes
- Commit `.env` file to git

### Token Rotation
- **Todoist:** Can be regenerated anytime at https://app.todoist.com/app/settings/integrations/developer
- **TickTick:** Can be regenerated anytime from Settings → API Keys

---

## 🆘 General Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Nothing to export" | No items unchecked | Uncheck items you want to sync |
| "Configuration needed" | Token/credentials missing | Add token to `.env`, restart Flask |
| 401 Unauthorized | Wrong/expired token | Generate new token, update `.env` |
| Empty shopping list | No menu generated | Create a menu first |
| Flask won't start | Syntax error in `.env` | Check `.env` for quote/format errors |

---

## 📞 Support

- For technical issues: Check the service's own support
- For Pi-Menu bugs: Report on GitHub

---

**Last updated:** June 2026
