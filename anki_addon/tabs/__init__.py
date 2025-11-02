"""Cross-platform tab detection and classification helpers.

Exports:
- get_active_tab() -> tuple[str|None, str|None]
	Returns (title, url) for the active browser tab when supported, else (None, None).
- classify(url, title) -> str
	Re-export of the work-focused classifier: 'whitelist' | 'blacklist' | 'unclassified'.
"""

from __future__ import annotations

from typing import Tuple, Optional
import os
import platform
from ..log_util import log

# Re-export the classifier
from .work_filter import classify  # noqa: F401


def _get_tab_windows() -> Tuple[Optional[str], Optional[str]]:
	try:
		from .get_chrome_tab_windows import get_chrome_url_pywinauto  # type: ignore
	except Exception as e:
		log(e)
		return None, None
	try:
		title, url = get_chrome_url_pywinauto()
		return title, url
	except Exception:
		return None, None


def _get_tab_mac() -> Tuple[Optional[str], Optional[str]]:
	try:
		from .get_chrome_tab_mac import get_active_chrome_tab  # type: ignore
	except Exception:
		return None, None
	try:
		title, url = get_active_chrome_tab()
		return title, url
	except Exception:
		return None, None


def get_active_tab() -> Tuple[Optional[str], Optional[str]]:
	"""Return (title, url) of the active browser tab when supported.

	Windows: Uses UI Automation (pywinauto) for Chromium browsers.
	macOS: Uses AppleScript for Google Chrome.
	Others: Returns (None, None).
	"""
	try:
		sysname = platform.system()
		if os.name == 'nt' and sysname == 'Windows':
			return _get_tab_windows()
		if sysname == 'Darwin':
			return _get_tab_mac()
		return (None, None)
	except Exception:
		return (None, None)

