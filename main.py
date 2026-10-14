"""Start the MySQL API used by the React/TanStack frontend."""
from __future__ import annotations

from api_server import app
from database.connection import initialize_database
from database.database_manager import seed_defaults


if __name__ == "__main__":
    initialize_database()
    seed_defaults()
    app.run(host="127.0.0.1", port=5000, debug=False)
