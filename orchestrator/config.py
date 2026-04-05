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
CLONE_DIR = Path("/tmp/eureka-clones")

# API keys
# ANTHROPIC_API_KEY is not used — agents use claude-agent-sdk with OAuth.
# agent_runner.py strips this from the environment to prevent auth poisoning.
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# LangSmith (optional)
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "eureka")

# Limits
MAX_FILES_PER_RUN = 50
MAX_LINES_PER_FILE = 200

# Logging
logger = logging.getLogger("eureka")
logging.basicConfig(level=logging.INFO)
