"""Entry point used to package the app into a single Windows .exe.

This does NOT contain any app logic — it just boots Streamlit's own CLI
against the bundled app.py, the same way `streamlit run app.py` does from
a terminal, so the packaged .exe behaves identically to the local dev run.
"""
import os
import sys

import streamlit.web.cli as stcli


def resource_path(relative_path: str) -> str:
    """Resolve a path that works both unpacked and inside a PyInstaller bundle."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)


if __name__ == "__main__":
    sys.argv = [
        "streamlit",
        "run",
        resource_path("app.py"),
        "--global.developmentMode=false",
        "--server.headless=false",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(stcli.main())
