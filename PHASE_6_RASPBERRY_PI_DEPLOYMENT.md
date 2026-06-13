#
# Pi-Menu Phase 6: Raspberry Pi Deployment
# Author:  nobody174 (nobodylearn174@gmail.com)
# Repo:    https://github.com/nobody174/Pi-Menu
# License: All rights reserved © 2025 nobody174
#

# Phase 6: Raspberry Pi Deployment

## Overview

Deploy Pi-Menu to Raspberry Pi 2 B for 24/7 operation with automatic menu generation every Saturday at 9 AM.

## Hardware Setup

- **Device:** Raspberry Pi 2 B
- **OS:** Raspberry Pi OS Lite (Debian)
- **IP Address:** 10.0.0.54
- **Username:** vartdalffs
- **Python Version:** 3.13.5
- **Hostname:** Pi-Menu

## Architecture

```
Windows PC (Developer)
    ↓
    ├── /data/menus/ (shared)
    ├── /data/recipes_db.json (shared)
    └── /data/weekly_menu.json (synced)
    ↓
Raspberry Pi (Production)
    ├── Pi-Menu application
    ├── systemd service (pi-menu.service)
    ├── Scheduled tasks (menu generation @ Sat 9 AM)
    └── 24/7 Flask server (optional: for local access)
```

## Phase 6 Steps

### Step 1: Clone Pi-Menu on Raspberry Pi

SSH into your Pi:

```bash
ssh vartdalffs@10.0.0.54
```

Clone the project:

```bash
cd ~
git clone https://github.com/nobody174/Pi-Menu.git
cd Pi-Menu
```

### Step 2: Install Dependencies on Pi

```bash
# Update package manager
sudo apt-get update
sudo apt-get upgrade -y

# Install Python dependencies
pip install -r requirements.txt

# Install additional dependencies for Pi
pip install schedule apscheduler
pip install requests python-dotenv

# Install Playwright (for recipe scraping, if needed)
pip install playwright
python -m playwright install chromium
```

Note: The `--break-system-packages` flag is needed on Pi OS:

```bash
pip install -r requirements.txt --break-system-packages
```

### Step 3: Set Up Environment Variables

Create `.env` on the Pi:

```bash
nano ~/.env
```

Add:

```env
#
# Pi-Menu Environment Variables - Raspberry Pi
# DO NOT COMMIT THIS FILE TO GIT
#

# Azure / Microsoft Graph API (for To Do sync)
AZURE_CLIENT_ID=6a554392-f3fb-4e8e-b85c-4970711ea412
AZURE_TENANT_ID=d450370d-b4f6-4ee6-916c-1d3c2091d1a3
AZURE_USERNAME=vartdal@gmail.com
AZURE_PASSWORD=your_app_password_here

# Scheduler
SCHEDULE_ENABLED=true
SCHEDULE_DAY=saturday
SCHEDULE_HOUR=9
SCHEDULE_MINUTE=0

# Flask (optional, for local web access)
FLASK_ENV=production
FLASK_DEBUG=false
FLASK_PORT=5000
```

Save: `Ctrl+X`, then `Y`, then `Enter`

### Step 4: Create systemd Service

Create the service file:

```bash
sudo nano /etc/systemd/system/pi-menu.service
```

Copy this content:

```ini
[Unit]
Description=Pi-Menu Weekly Menu Generator
After=network.target
Wants=pi-menu.timer

[Service]
Type=simple
User=vartdalffs
WorkingDirectory=/home/vartdalffs/Pi-Menu
Environment="PATH=/home/vartdalffs/.local/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/home/vartdalffs/.env
ExecStart=/usr/bin/python3 -m core.menu_generator

# Restart policy
Restart=on-failure
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pi-menu

[Install]
WantedBy=multi-user.target
```

Save and exit.

### Step 5: Create systemd Timer (Scheduler)

This runs menu generation every Saturday at 9 AM:

```bash
sudo nano /etc/systemd/system/pi-menu.timer
```

Copy:

```ini
[Unit]
Description=Pi-Menu Weekly Schedule
Requires=pi-menu.service

[Timer]
OnCalendar=Sat *-*-* 09:00:00
Persistent=true
AccuracySec=1min

[Install]
WantedBy=timers.target
```

Save and exit.

### Step 6: Enable and Start Services

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable the timer to start on boot
sudo systemctl enable pi-menu.timer

# Start the timer
sudo systemctl start pi-menu.timer

# Check status
sudo systemctl status pi-menu.timer

# View upcoming runs
sudo systemctl list-timers pi-menu.timer
```

### Step 7: Verify Setup

Check that everything is working:

```bash
# Check service status
sudo systemctl status pi-menu.timer

# View logs
sudo journalctl -u pi-menu -f

# Run menu generation manually to test
cd ~/Pi-Menu
python3 -c "from core.menu_generator import MenuGenerator; g = MenuGenerator(); g.run()"
```

### Step 8: Data Synchronization

To sync data between Windows PC and Pi, you have options:

**Option A: Manual Sync (Simple)**
```bash
# On Windows PC, copy data to Pi
scp -r D:\Claude AI Projects\projects\Pi-Menu\data\* vartdalffs@10.0.0.54:~/Pi-Menu/data/

# Or from Pi back to Windows
scp -r vartdalffs@10.0.0.54:~/Pi-Menu/data\weekly_menu.json D:\Claude AI Projects\projects\Pi-Menu\data\
```

**Option B: rsync (Automatic)**
```bash
# Install rsync on both systems
sudo apt-get install rsync

# Sync from Windows to Pi (Windows terminal)
rsync -avz D:\Claude AI Projects\projects\Pi-Menu\data\ vartdalffs@10.0.0.54:~/Pi-Menu/data/
```

**Option C: Network Share (Recommended)**
- Set up SMB/NFS share on Windows
- Mount on Pi
- Both systems read/write same folder

### Step 9: Optional - Flask Server on Pi

If you want the Pi to also run the web interface:

```bash
# Create another systemd service for Flask
sudo nano /etc/systemd/system/pi-menu-web.service
```

```ini
[Unit]
Description=Pi-Menu Flask Web Server
After=network.target

[Service]
Type=simple
User=vartdalffs
WorkingDirectory=/home/vartdalffs/Pi-Menu
EnvironmentFile=/home/vartdalffs/.env
ExecStart=/usr/bin/python3 pi-deployment/flask_app.py

Restart=on-failure
RestartSec=10

StandardOutput=journal
StandardError=journal
SyslogIdentifier=pi-menu-web

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pi-menu-web
sudo systemctl start pi-menu-web

# Access from Windows browser: http://10.0.0.54:5000
```

## Maintenance

### View Logs

```bash
# Current menu generation logs
sudo journalctl -u pi-menu -n 50

# Follow live logs
sudo journalctl -u pi-menu -f

# View Flask logs (if running)
sudo journalctl -u pi-menu-web -f
```

### Manual Menu Generation

```bash
ssh vartdalffs@10.0.0.54
cd ~/Pi-Menu
python3 -c "from core.menu_generator import MenuGenerator; MenuGenerator().run(num_dinners=6, save=True)"
```

### Check Scheduled Runs

```bash
sudo systemctl list-timers pi-menu.timer
sudo systemctl status pi-menu.timer
```

### Modify Schedule

Edit the timer:

```bash
sudo systemctl edit pi-menu.timer
```

Change `OnCalendar=Sat *-*-* 09:00:00` to your desired schedule.

Then reload:

```bash
sudo systemctl daemon-reload
sudo systemctl restart pi-menu.timer
```

## Troubleshooting

### Service Won't Start

```bash
sudo systemctl status pi-menu.timer
sudo journalctl -u pi-menu -n 20
```

Check for:
- Python module import errors
- Missing dependencies
- File permission issues

### Timer Not Firing

```bash
# Check systemd-logind
sudo journalctl -u systemd-logind -f

# Verify timer syntax
sudo systemctl start pi-menu.timer --no-block
```

### Data Not Syncing

```bash
# Check file permissions
ls -la ~/Pi-Menu/data/

# Test rsync
rsync -avz vartdalffs@10.0.0.54:~/Pi-Menu/data/ D:\Claude AI Projects\projects\Pi-Menu\data\
```

### Menu Generation Fails

```bash
# Run manually to see error
python3 ~/Pi-Menu/core/menu_generator.py

# Check recipe database
ls -la ~/Pi-Menu/data/recipes_db.json
```

## Performance Notes

**Raspberry Pi 2 B Considerations:**
- Menu generation takes ~10-15 seconds
- Recipe scraping is slower (avoid on Pi, do on Windows instead)
- Keep Flask server off unless needed (saves RAM)
- Monitor disk space (Pi OS Lite uses minimal space)

```bash
# Check disk usage
df -h

# Check memory usage
free -h

# Check temperature
/opt/vc/bin/vcgencmd measure_temp
```

## Security Notes

✅ **Secure:**
- `.env` file on Pi (not committed to git)
- SSH key-based auth recommended
- systemd runs service with limited user

⚠️ **To Do Integration:**
- Store app password securely in `.env`
- Never hardcode credentials
- Consider rotating credentials periodically

## Backup Strategy

```bash
# Backup Pi-Menu on Windows
rsync -avz vartdalffs@10.0.0.54:~/Pi-Menu/ D:\Backups\Pi-Menu\

# Backup weekly menu
scp vartdalffs@10.0.0.54:~/Pi-Menu/data/weekly_menu.json D:\Backups\menus\menu_$(date +%Y%m%d).json
```

## Next Steps

After Phase 6 is complete:

1. ✅ Test menu generation runs on schedule
2. ✅ Verify data syncing works
3. ✅ Check Flask web server (if enabled)
4. ✅ Monitor logs for 2-3 weeks
5. 🔄 Return to Phase 5: Fix To Do sync
6. 📱 Deploy To Do integration
7. 🚀 Full production deployment

## Files Needed on Pi

```
~/Pi-Menu/
├── core/
│   ├── menu_generator.py
│   ├── ingredient_deduplicator.py
│   └── todo_sync.py (for Phase 5)
├── pi-deployment/
│   └── flask_app.py (if web server enabled)
├── data/
│   ├── recipes_db.json
│   ├── menus/ (category folders)
│   └── weekly_menu.json
├── config.py
└── requirements.txt
```

## Summary

You now have a fully automated Pi-Menu system:
- 🍓 Runs 24/7 on Raspberry Pi
- 📅 Generates menus automatically every Saturday at 9 AM
- 💾 Syncs data with Windows PC
- 📊 Can serve web dashboard on local network
- 📝 Full logging and monitoring
- 🔄 Easy to maintain and troubleshoot

---

*Built with assistance from Claude Code by Anthropic.*
