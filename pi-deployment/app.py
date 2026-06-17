#!/usr/bin/env python3
#
# Pi-Menu - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Pi-Menu-Public
# License: MIT
#

"""
Pi-Menu Main Application Entry Point
Runs Flask app with background scheduler
"""

import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from flask_app import app
from scheduler import MenuScheduler

def run_app_with_scheduler():
    logger.info("=" * 60)
    logger.info("Pi-Menu Application Starting")
    logger.info("=" * 60)

    scheduler = MenuScheduler()

    if scheduler.start():
        logger.info("Background scheduler started")
    else:
        logger.warning("Failed to start scheduler - Flask will run without scheduling")

    try:
        logger.info("Starting Flask app on http://0.0.0.0:5000")
        app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        scheduler.shutdown()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {e}")
        scheduler.shutdown()
        sys.exit(1)

def run_app_only():
    logger.info("=" * 60)
    logger.info("Pi-Menu Flask App Starting (no scheduler)")
    logger.info("=" * 60)

    try:
        logger.info("Starting Flask app on http://0.0.0.0:5000")
        app.run(host='0.0.0.0', port=5001, debug=False)
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)

def run_manual_generation():
    logger.info("Running manual menu generation...")

    scheduler = MenuScheduler()
    scheduler.run_once()

    logger.info("Menu generation complete")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Pi-Menu Application')
    parser.add_argument('--no-scheduler', action='store_true', help='Run Flask without scheduler')
    parser.add_argument('--generate', action='store_true', help='Generate menu once and exit')
    args = parser.parse_args()

    if args.generate:
        run_manual_generation()
    elif args.no_scheduler:
        run_app_only()
    else:
        run_app_with_scheduler()
