"""Regression guard: version must stay consistent across config/main/web_server.

Guards against regressions of:
  - 2026-08-03: web_server.py hardcoded VERSION="0.8.0" (should use config.VERSION)
  - 2026-08-08: main.py module docstring still said v0.4.0
"""

import os
import re
import sys

# Add shadow-cli to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from web_server import VERSION as WEB_VERSION

MAIN_SRC = os.path.join(os.path.dirname(__file__), "..", "main.py")


def test_config_version_is_expected():
    assert config.VERSION == "0.9.2"


def test_web_server_version_matches_config():
    assert WEB_VERSION == config.VERSION


def test_main_docstring_matches_config():
    with open(MAIN_SRC, encoding="utf-8") as fh:
        head = fh.read(400)  # docstring lives at the top of the file
    assert re.search(rf"v{re.escape(config.VERSION)}", head), (
        f"main.py docstring should reference v{config.VERSION}"
    )
