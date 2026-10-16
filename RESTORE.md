# InkSpeed Database Restore

The repository includes `backup_db.bat`, which writes a timestamped SQL dump
under `backups\` using the XAMPP MySQL binaries.

## Command-line restore

From a Command Prompt in the repository root:

```bat
C:\xampp\mysql\bin\mysql.exe -u root -p inkspeed_db < backups\inkspeed_db_YYYYMMDD_HHMMSS.sql
```

For the default local XAMPP installation, omit `-p` when the root password is
empty. Set `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, and `MYSQL_PASSWORD` when
the server uses different credentials.

## phpMyAdmin restore

1. Start MySQL in XAMPP and open `http://localhost/phpmyadmin`.
2. Select or create `inkspeed_db`.
3. Open **Import**, choose the `.sql` dump, and click **Import**.
4. Restart the Flask API and verify `/api/health`, history, and leaderboard.

Always test a restore on a copy of the database before replacing a production
database.
