@echo off
echo Setting up Heroku deployment...

REM Check if Heroku CLI is installed
heroku --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Heroku CLI not found. Installing...
    REM Download and install Heroku CLI for Windows
    powershell -Command "Invoke-WebRequest -Uri 'https://cli-assets.heroku.com/heroku-x64.exe' -OutFile 'heroku.exe'"
    move heroku.exe C:\Windows\System32\
    echo Heroku CLI installed.
) else (
    echo Heroku CLI is already installed.
)

REM Login to Heroku
echo Logging into Heroku...
heroku login

REM Initialize git if not already
if not exist .git (
    echo Initializing git repository...
    git init
    git add .
    git commit -m "Initial commit for deployment"
) else (
    echo Git repository already exists.
    git add .
    git commit -m "Update for deployment"
)

REM Create Heroku app
echo Creating Heroku app...
heroku create your-smart-post-office-app --region eu

REM Set environment variables (replace with your actual values)
heroku config:set SECRET_KEY=your-secret-key-change-this
heroku config:set ADMIN_USERNAME=admin
heroku config:set ADMIN_PASSWORD=admin123
REM Add other env vars as needed: MAIL_SERVER, etc.

REM Deploy
echo Deploying to Heroku...
git push heroku main

REM Open the app
heroku open

echo Deployment complete! Your app is live on Heroku.
pause
