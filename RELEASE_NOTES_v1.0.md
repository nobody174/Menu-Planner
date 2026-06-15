# Pi-Menu Public Release v1.0

**Release Date:** June 15, 2026  
**Status:** Ready for Public Release  
**License:** MIT  

## What's Included

Pi-Menu v1.0 is a complete, open-source weekly meal planner for families.

### Core Features

✓ **Recipe Management** - Store unlimited family recipes  
✓ **Weekly Menu Generation** - Automated menu creation with variety  
✓ **Shopping Lists** - Automatic ingredient deduplication  
✓ **Bilingual Interface** - Norwegian & English with one-click toggle  
✓ **Responsive Web App** - Works on desktop, tablet, mobile  
✓ **Multiple Themes** - 9 beautiful themes to customize UI  
✓ **Category System** - Organize recipes (Family, Quick, Vegetarian, Fish, Meat, Other)  
✓ **Open Source** - 100% free, MIT licensed, no tracking  

### Optional Features

✓ **Microsoft To Do Sync** - Push menus/shopping lists to your To Do lists  
✓ **Email Notifications** - Weekly menu summaries via email  
✓ **Background Scheduler** - Automatic menu generation on schedule  

### Technical

✓ **No Database Server** - Uses JSON files for data storage  
✓ **Raspberry Pi Ready** - Deploy on Pi with systemd service  
✓ **Python 3.9+** - Pure Python/Flask application  
✓ **No API Keys** - All data local, optional cloud sync only  

## What's NOT Included

- Hello Fresh recipe scraping (removed for legal reasons)
- Personal recipe data (you provide your own)
- Hardcoded credentials (all moved to .env)
- Personal email addresses (all removed)
- Proprietary content (all original open source code)

## Removed from Private Version

The public version removed:

- ~~Hello Fresh web scraper~~ → Users provide recipes via Excel template
- ~~139 Hello Fresh recipes~~ → 10 generic sample recipes included
- ~~Hardcoded Azure credentials~~ → All moved to .env template
- ~~Personal email (vartdal@gmail.com)~~ → Uses environment variable
- ~~Family name 'Vartdals'~~ → Parameterized to {Family_Name}
- ~~Proprietary headers~~ → MIT license headers added
- ~~Personal comments~~ → Removed from code and templates

## Installation

```bash
git clone https://github.com/nobody174/Pi-Menu-Public.git
cd Pi-Menu-Public
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.template .env
python3 pi-deployment/app.py
```

Visit: http://localhost:5000

## Documentation

- **README.md** - Project overview & quick start
- **docs/SETUP_GUIDE.md** - Detailed installation & configuration
- **docs/EXCEL_GUIDE.md** - How to add your recipes
- **docs/FAQ.md** - Troubleshooting & common questions
- **ARCHITECTURE.md** - System design & data flow

## System Requirements

- **Python:** 3.9 or higher
- **OS:** Windows, Mac, Linux, or Raspberry Pi
- **Browser:** Any modern browser (Chrome, Firefox, Safari, Edge)
- **Optional:** Microsoft account (for To Do sync)

## Deployment Options

1. **Local Development** - `python3 pi-deployment/app.py`
2. **Raspberry Pi** - Systemd service (instructions in docs)
3. **Docker** - Docker support ready (build file included)
4. **Server** - Any Linux server with Python 3.9+

## Language Support

- **Norwegian** (Norsk) - 🇳🇴 - Default
- **English** - 🇬🇧 - Full support
- Switch in Settings → Språk

## Themes

9 built-in themes:
1. Warm & Modern
2. Terracotta & Sage
3. Apple Fitness
4. Brutalist
5. Chalkboard Bistro
6. Coastal Kitchen
7. Forest Forager
8. Kjøkkenhylle
9. Pop Art Diner

## Known Limitations

- Recipe import requires Excel template (manual entry or via web form)
- Up to ~1000 recipes recommended (performance not tested beyond)
- To Do sync requires Microsoft account & Azure app registration
- Email notifications require Gmail app password (for security)

## Breaking Changes from Private Version

If migrating from the private version:

1. **Recipe Database** - Must re-import recipes using Excel template
2. **Configuration** - Use .env file instead of hardcoded values
3. **No More Scraping** - Users provide recipes, not scraped
4. **URL Change** - GitHub repo changed to Pi-Menu-Public

## Roadmap / Future Enhancements

Potential features for future versions:

- [ ] Recipe sharing between users
- [ ] Dietary restriction filtering (keto, vegan, etc.)
- [ ] Nutrition tracking
- [ ] Grocery list integration (price lookup)
- [ ] Multi-family households support
- [ ] Recipe rating & favorites on dashboard
- [ ] Google Calendar integration
- [ ] Meal prep preparation time estimate
- [ ] Ingredient substitution suggestions
- [ ] Mobile app (native iOS/Android)

## Support & Contributing

- **GitHub Issues:** Report bugs or request features
- **GitHub Discussions:** General questions
- **Patreon:** Support the creator
- **Pull Requests:** Contributions welcome!

## Credits

**Creator:** nobody174 (nobodylearn174@gmail.com)

**Built With:**
- Flask (web framework)
- APScheduler (task scheduling)
- Jinja2 (templating)
- Fuzzy matching (ingredient deduplication)
- Python standard library

**Special Thanks:**
- Claude Code (Anthropic) - Used for development
- GitHub - Version control & hosting
- Open source community

## License

MIT License - See LICENSE file

This means:
- ✓ Free for commercial use
- ✓ Free for personal use
- ✓ Can modify and redistribute
- ✓ Must include license & attribution

## Security & Privacy

**Security:**
- No hardcoded secrets
- All credentials in .env (not committed)
- HTTPS support built in
- CSRF protection
- Session security enabled

**Privacy:**
- All data stored locally
- No tracking or analytics
- No personal data collection
- Optional cloud sync only
- Open source (you can audit code)

## Changelog

### v1.0.0 (June 15, 2026) - Initial Public Release

**NEW:**
- Complete project restructure for public release
- Removed all Hello Fresh content
- Added bilingual support (Norwegian/English)
- Parameterized configuration (family name, etc.)
- Added measurement conversion system
- Created comprehensive documentation
- Added 10 sample recipes
- Implemented dynamic category system

**REMOVED:**
- Hello Fresh recipe scraper
- All proprietary Hello Fresh recipes (139 removed)
- Hardcoded Azure credentials
- Hardcoded email addresses
- Personal names from code

**FIXED:**
- Security: All secrets moved to .env
- Legal: All HelloFresh references removed
- Code: All headers updated with MIT license
- Docs: Complete documentation suite

## Future Release Plans

- v1.1 - User authentication & multi-user support
- v1.2 - Recipe sharing & community features
- v2.0 - Native mobile app

## Getting Help

1. Check [FAQ.md](docs/FAQ.md) for common questions
2. Read [SETUP_GUIDE.md](docs/SETUP_GUIDE.md) for setup issues
3. Check logs in `logs/` directory
4. Open GitHub issue for bugs
5. Contact creator on Patreon

## Thank You

Thank you for using Pi-Menu! We hope it helps your family enjoy better meal planning.

If you like it, please:
- Star on GitHub
- Share with friends/family
- Support on Patreon
- Report bugs & suggest features

---

**Pi-Menu v1.0** - Made with care by [nobody174](https://github.com/nobody174)

[GitHub](https://github.com/nobody174/Pi-Menu-Public) | [Patreon](https://www.patreon.com/c/Nobody174) | [Issues](https://github.com/nobody174/Pi-Menu-Public/issues)
