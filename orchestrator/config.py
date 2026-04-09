"""Eureka configuration: env vars, paths, constants."""

import os
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Directories
MEMORY_DIR = Path("memory")
AUDIT_DIR = Path("audit")
TEMPLATE_PATH = MEMORY_DIR / "_template.md"
SKILLS_DIR = Path(".claude/skills")
# API keys
# ANTHROPIC_API_KEY is not used — agents use claude-agent-sdk with OAuth.
# agent_runner.py strips this from the environment to prevent auth poisoning.
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# LangSmith (optional)
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "eureka")

# Logging
logger = logging.getLogger("eureka")
logging.basicConfig(level=logging.INFO)
