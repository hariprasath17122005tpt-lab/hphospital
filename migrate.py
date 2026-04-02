#!/usr/bin/env python3
"""
Hospital Management System — Database Migration Entry Point
===========================================================

This script is used to initialize Flask-Migrate, run migrations, and
upgrade the database schema without losing data.

COMMANDS (run inside the container or with venv active):
  # 1. First-time only: initialize the migrations folder
  flask db init

  # 2. Auto-generate a migration after model changes
  flask db migrate -m "describe your change"

  # 3. Apply pending migrations to the target DB (RDS or local)
  flask db upgrade

  # 4. Roll back last migration
  flask db downgrade

  # 5. Show migration history
  flask db history

USAGE on AWS EC2:
  python migrate.py upgrade

USAGE locally (with .env loaded):
  python migrate.py upgrade
"""
import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv('.env.production' if os.path.exists('.env.production') else '.env')

from flask.cli import FlaskGroup
from run import app

# Allow `python migrate.py <command>` as a convenience wrapper
cli = FlaskGroup(app)

if __name__ == '__main__':
    cli()
