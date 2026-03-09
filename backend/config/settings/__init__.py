"""
Settings package for E.P Basic School Fee Management System.
Automatically loads appropriate settings based on environment.
"""

from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env()

# Prefer backend/.env for local Django commands, then root .env for Docker/root usage
backend_env = BASE_DIR / ".env"
root_env = BASE_DIR.parent / ".env"

if backend_env.exists():
    environ.Env.read_env(backend_env)
elif root_env.exists():
    environ.Env.read_env(root_env)

environment = env("DJANGO_ENV", default="development").lower()

if environment == "production":
    from .production import *
else:
    from .development import *