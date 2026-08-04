@echo off
echo Setting up Render deployment...

REM Check if Render CLI is installed
render --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Render CLI not found. Installing...
    npm install -g @render/cli
    echo Render CLI installed.
) else (
    echo Render CLI is already installed.
)

REM Login to Render
echo Logging into Render...
render login

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

REM Create Render service
echo Creating Render web service...
render services create --name smart-post-office --type web --repo https://github.com/yourusername/smart-post-office --branch main --runtime python3 --build-command "pip install -r requirements.txt" --start-command "gunicorn wsgi:app"

REM Note: Replace 'yourusername' with your GitHub username
REM You need to push the code to GitHub first
echo.
echo IMPORTANT: Before running this script fully, you need to:
echo 1. Create a GitHub repository
echo 2. Push your code to GitHub: git remote add origin https://github.com/yourusername/smart-post-office.git && git push -u origin main
echo 3. Then run this script again to create the Render service
echo.
echo Alternatively, use the Render web dashboard to create a web service from your GitHub repo.

pause
