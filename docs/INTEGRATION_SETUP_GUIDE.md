# Pi-Menu Shopping List Integration Setup Guide

Complete step-by-step instructions for syncing your shopping list to various task managers and export formats.

---

## 📋 Table of Contents

1. [Export Formats](#export-formats) - CSV, JSON, Text, ICS
2. [Microsoft To Do](#microsoft-to-do) - Built-in task manager
3. [Todoist](#todoist) - Popular task manager
4. [TickTick](#ticktick) - Powerful task management
5. [Apple Reminders](#apple-reminders) - Native iOS/macOS

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

## Microsoft To Do

### ✅ What You Need
- A Microsoft account (Outlook, Live, or work account)
- Azure App Registration (one-time setup, 10 minutes)

### 🔗 Helpful Links
- **Sign up for Microsoft account:** https://account.microsoft.com/account
- **Azure Portal:** https://portal.azure.com
- **Microsoft To Do app:** https://to-do.office.com/tasks/
- **Check your synced items:** https://to-do.office.com/tasks/

### 📝 Step-by-Step Setup

#### Step 1: Register an Azure App

1. Go to **https://portal.azure.com**
2. **Sign in** with your Microsoft account
3. **Search for "App registrations"** in the top search bar
4. Click **"New registration"**
5. Fill in the form:
   - **Name:** `Pi-Menu`
   - **Supported account types:** Select "Accounts in any organizational directory and personal Microsoft accounts"
6. Click **"Register"**

#### Step 2: Copy Your Credentials

You're now on the app overview page. **Copy these 3 values** (you'll need them):

1. **Application (client) ID** - Copy this
2. **Directory (tenant) ID** - Copy this
3. **Client Secret** (need to create it):
   - Click **"Certificates & secrets"** on the left menu
   - Click **"New client secret"**
   - Give it a description: `Pi-Menu`
   - Click **"Add"**
   - **Copy the secret value immediately** (it only shows once!)

#### Step 3: Add Redirect URL

1. Click **"Authentication"** on the left menu
2. Click **"Add a platform"** → select **"Web"**
3. Add this Redirect URI:
   ```
   http://localhost:5000/callback
   ```
4. Click **"Configure"**

#### Step 4: Add Credentials to Pi-Menu

1. Find your `.env` file (in the Pi-Menu main folder)
   - If you don't have one, copy `.env.template` and rename to `.env`
2. Find these lines:
   ```
   AZURE_CLIENT_ID=
   AZURE_CLIENT_SECRET=
   AZURE_TENANT_ID=
   ```
3. Paste your values:
   ```
   AZURE_CLIENT_ID=abc123def456...
   AZURE_CLIENT_SECRET=xyzABC123def456...
   AZURE_TENANT_ID=def456ghi789...
   ```
4. Save the file
5. **Restart Flask**

#### Step 5: First-Time Authorization

**Important:** The first time you use Microsoft To Do, you need to authorize Pi-Menu:

1. **Go to:** `http://localhost:5000/callback` (or your Pi's address)
2. **Sign in** with your Microsoft account
3. **Grant permissions** when prompted
4. **You'll be redirected back** - authorization is complete!

This only needs to be done once. Pi-Menu caches your token locally.

#### Step 6: Use It!

1. **Open Pi-Menu** in your browser
2. **Go to Shopping List** page
3. Click **"📤 Export & Sync"** button
4. Click **"🔵 Microsoft To Do"**
5. **Items sync automatically!** 🎉

#### Step 7: Verify It Works

1. Go to **https://to-do.office.com/tasks/**
2. Look for a list called **"Pi-Menu Handleliste"**
3. You should see your synced items there! ✅

### 🔄 Sync Again Later

- Just click the "🔵 Microsoft To Do" button again
- No additional login needed
- Your credentials are cached locally

### ❓ Troubleshooting
| Problem | Solution |
|---------|----------|
| "Configuration needed" error | Check that AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID are filled in `.env`, then restart Flask |
| "Not signed in" message | Click "🔵 Microsoft To Do" button → you'll be redirected to sign in |
| Items not appearing | Check https://to-do.office.com/tasks/ to see if items are there |

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
