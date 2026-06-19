"""Dev server: venv/Scripts/python.exe run.py -> http://localhost:3000
Port is configurable via the PORT env var (default 3000)."""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "3000"))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
