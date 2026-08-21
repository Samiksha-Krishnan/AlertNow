"""
Alert Now — civic incident reporting app.

Run:
    python app.py

Then open http://localhost:5000

(App construction lives in factory.py — see the comment there for why.)
"""

import os

from factory import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
