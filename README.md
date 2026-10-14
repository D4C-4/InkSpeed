# InkSpeed

## Project Description

InkSpeed is a typing-speed application for desktop use. Players can create
profiles, practise in Classic, Memory Rush, and Key Chaos modes, and review
their results through history, leaderboards, challenges, and achievements.

The Python backend stores application data in MySQL. The React frontend is
served by Vite and can be opened in a browser or launched in an Electron
desktop window.

## Tech Stack

- Python
- MySQL
- Electron
- React
- TypeScript
- Vite
- TanStack Router

## Installation

### Prerequisites

Install the following on the development or presentation laptop:

- Python 3.10 or newer
- Node.js LTS and npm
- XAMPP (Apache is optional; MySQL is required)
- Git

### Clone the repository

```powershell
git clone <repository-url>
cd "SDF04 Project"
```

### Backend setup

Create and activate a virtual environment, then install the Python
dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run the commands with the virtual
environment interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Database setup

1. Start MySQL in the XAMPP Control Panel.
2. Open phpMyAdmin at `http://localhost/phpmyadmin`.
3. Create a database named `inkspeed_db`, or allow the backend to create it
   automatically.
4. Import `database/schema.sql`.
5. Import `database/seed.sql`.

The default connection is `127.0.0.1:3306` with user `root` and an empty
password. If your MySQL credentials differ, set `MYSQL_HOST`, `MYSQL_PORT`,
`MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DATABASE` before starting the
backend.

### Frontend setup

```powershell
cd web
npm install
```

### Run development mode

From `web`:

```powershell
npm run dev
```

Open the URL printed by Vite, usually `http://localhost:5173`.

### Run the backend separately

From the repository root, in a second terminal:

```powershell
.\.venv\Scripts\python.exe main.py
```

The API listens on `http://127.0.0.1:5000`.

### Run Electron

From `web`:

```powershell
npm run electron
```

`npm run desktop` is also available as an equivalent command. Electron
starts the backend and Vite development server automatically, so ensure
MySQL is running and the root `.venv` has been created first.

## Project Structure

```text
database/       MySQL schema, seed data, connection, and repositories
game/           Typing modes and game rules
models/         Backend domain models
tests/          Python tests
legacy/         Earlier desktop UI resources retained for reference
web/src/        React, TypeScript, routes, components, and frontend tests
web/electron/   Electron main process
api_server.py   Flask API used by the frontend
main.py         Backend startup entry point
requirements.txt Python dependencies
```

## Useful Commands

From `web`:

```powershell
npm run build
npm run lint
npm run test
```

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Troubleshooting

- **MySQL connection errors:** Start MySQL in XAMPP and verify the
  `MYSQL_*` environment variables. The default user is `root` with an empty
  password.
- **Database or table does not exist:** Import
  `database/schema.sql`, then `database/seed.sql` in phpMyAdmin. The backend
  also initializes the schema when it starts.
- **Electron cannot start Python:** Create the root `.venv` and install
  `requirements.txt`; Electron expects
  `.venv\Scripts\python.exe`.
- **Port already in use:** Stop the process using port 5000 or 5173 before
  starting the application.
- **Frontend dependency errors:** From `web`, remove the local
  `node_modules` directory and run `npm install` again.
- **PowerShell activation errors:** Use
  `.\.venv\Scripts\python.exe` directly instead of activating the environment.
