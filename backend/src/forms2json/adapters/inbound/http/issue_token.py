"""Prints a demo JWT signed with the configured secret.

Usage: uv run python -m forms2json.adapters.inbound.http.issue_token [subject]
"""

import sys

from forms2json.adapters.inbound.http.auth import issue_token
from forms2json.config import get_settings

if __name__ == "__main__":
    print(issue_token(get_settings(), sys.argv[1] if len(sys.argv) > 1 else "demo"))
