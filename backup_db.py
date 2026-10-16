"""Create a timestamped MariaDB dump using the XAMPP client binaries."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
MYSQL_BIN = Path(os.getenv("MYSQL_BIN", r"C:\xampp\mysql\bin"))
HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
PORT = os.getenv("MYSQL_PORT", "3306")
USER = os.getenv("MYSQL_USER", "root")
DATABASE = os.getenv("MYSQL_DATABASE", "inkspeed_db")
password = os.getenv("MYSQL_PASSWORD")
output = ROOT / "backups" / f"{DATABASE}_{datetime.now():%Y%m%d_%H%M%S}.sql"
output.parent.mkdir(exist_ok=True)

command = [
    str(MYSQL_BIN / "mysqldump.exe"),
    "-h",
    HOST,
    "-P",
    PORT,
    "-u",
    USER,
]
if password:
    command.append(f"-p{password}")
command.append(DATABASE)

with output.open("w", encoding="utf-8", newline="") as dump:
    subprocess.run(command, stdout=dump, check=True)

print(f"Backup written to {output}")
