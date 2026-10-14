# InkSpeed Presentation Setup

This guide prepares a Windows presentation laptop from a fresh clone.

## 1. Install the prerequisites

Install:

- Git
- Python 3.10 or newer
- Node.js LTS
- XAMPP

During XAMPP installation, include MySQL. Apache is not required by InkSpeed,
but may be installed with the standard XAMPP package.

## 2. Clone InkSpeed

```powershell
git clone <repository-url>
cd "SDF04 Project"
```

## 3. Start MySQL with XAMPP

1. Open the XAMPP Control Panel.
2. Start **MySQL**.
3. Open `http://localhost/phpmyadmin`.

## 4. Import the database scripts

1. In phpMyAdmin, create a database named `inkspeed_db`.
2. Select `inkspeed_db`.
3. Use **Import** and select `database/schema.sql`.
4. Import `database/seed.sql` in the same database.

The schema script creates the tables. The seed script adds the demo user,
achievements, and default challenges.

## 5. Install Python dependencies

From the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 6. Install Node dependencies

```powershell
cd web
npm install
```

## 7. Run the backend

Open a second PowerShell window, return to the repository root, and run:

```powershell
.\.venv\Scripts\python.exe main.py
```

Keep this window open. Confirm the API is available at
`http://127.0.0.1:5000/api/health`.

## 8. Run the frontend

In the `web` directory:

```powershell
npm run dev
```

Open the Vite URL shown in the terminal, normally
`http://localhost:5173`.

## 9. Run Electron

Stop the separately started backend and frontend if you want Electron to
manage both processes, then from `web` run:

```powershell
npm run electron
```

The equivalent existing command is `npm run desktop`. Electron starts the
Python backend and Vite server, then opens the InkSpeed desktop window.

## Presentation checks

- MySQL is running in XAMPP.
- `http://127.0.0.1:5000/api/health` returns `{"ok":true}`.
- A user can be selected or created.
- At least one game mode can be completed.
- History, leaderboard, challenges, and achievements load.
- The Electron window opens without a port or database error.
