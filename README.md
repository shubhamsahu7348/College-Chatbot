<<<<<<< HEAD
# MahaCollege AI Counselor

A Flask-based college admission chatbot for MCA colleges in Maharashtra. The app uses local college data and the Gemini API to answer questions about college fees, placements, intake, percentile chances, and whether a school is private or government.

## Features

- Search and display the top MCA colleges
- Show college placement details with average and highest packages
- Provide intake and fees information for colleges
- Answer private vs government college queries
- Return full college details when a specific college name is detected
- Percentile-based college matching with admission chances
- Structured HTML output for easy chatbot viewing

## Project Structure

- `app.py` — Flask backend and query logic
- `data/colleges.json` — local college dataset used by the bot
- `templates/index.html` — frontend chat UI
- `static/` — CSS and JS assets
- `.env` — environment variables (API key)
- `requirements.txt` — Python dependencies

## Requirements

- Python 3.11 or newer
- Git
- Gemini API key
- Windows PowerShell or another terminal

## Setup

1. Open a terminal in the project folder:
   ```powershell
   cd s:\college_chatbot
   ```

2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv .venv
   & .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root and add your Gemini API key:
   ```dotenv
   GEMINI_API_KEY=your_api_key_here
   ```

5. Start the Flask application:
   ```powershell
   python app.py
   ```

6. Open the web app in your browser:
   ```text
   http://127.0.0.1:5000
   ```

## Sample Queries

Try these example messages in the chat UI:

- `Top 10 MCA Colleges`
- `placement`
- `fees`
- `intake`
- `SPIT fees`
- `Bharti Vidyapeeth placement`
- `PCCOE admission process`
- `My percentile is 85`
- `Which colleges are government?`

## GitHub Upload Steps

If your repository is not yet initialized, run these commands from the project root:

```powershell
cd s:\college_chatbot

git init

git add .
git commit -m "Initial commit"
git branch -M main
# Replace this URL with your GitHub repository URL if needed
git remote add origin https://github.com/shubhamsahu7348/College-Chatbot.git
git push -u origin main
```

If the repo already exists and the remote is configured, use:

```powershell
git add .
git commit -m "Update project files"
git push origin main
```

## If Git is not on PATH

If `git` is not recognized, install Git from [https://git-scm.com/downloads](https://git-scm.com/downloads) and then reopen PowerShell.

## Deploying from GitHub

This repository can be hosted on Python-friendly deployment platforms such as:

- Render
- Railway
- Fly.io
- Heroku

After cloning from GitHub, use the same setup commands and start the app with:

```powershell
python app.py
```

> Note: GitHub Pages cannot host Flask backend apps directly.

## Notes

- Do not push `.env` to GitHub. It contains your API key.
- `.env` is already ignored by `.gitignore`.
- If you want to update the college dataset, edit `data/colleges.json`.

## Run from GitHub

To run the project after cloning from GitHub:

```powershell
git clone https://github.com/shubhamsahu7348/College-Chatbot.git
cd College-Chatbot
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# create .env with GEMINI_API_KEY
python app.py
```
=======
# College-Chatbot
>>>>>>> 37afb858773f29b82f9d9fe133483f0ec9e09e12
