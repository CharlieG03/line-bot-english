@echo off
echo ========================================
echo Line Bot Deployment Script
echo ========================================
echo.

REM Configure Git identity if not set
git config user.name >nul 2>&1
if errorlevel 1 (
    echo Git identity not configured. Let's set it up...
    set /p GIT_NAME="Enter your name: "
    set /p GIT_EMAIL="Enter your email: "
    
    git config --global user.name "%GIT_NAME%"
    git config --global user.email "%GIT_EMAIL%"
    echo Git identity configured!
    echo.
)

REM Check if git is initialized
if not exist .git (
    echo Initializing Git repository...
    git init
    
    echo Creating .gitignore...
    echo .env > .gitignore
    echo __pycache__/ >> .gitignore
    echo *.pyc >> .gitignore
    echo linebot_env/ >> .gitignore
    echo.
)

echo Adding files to git...
git add .

echo Committing changes...
git commit -m "Deploy dynamic Line Bot"

echo.
echo Enter your Heroku app name (e.g., my-english-bot):
set /p APP_NAME="App name: "

echo.
echo Creating Heroku app...
heroku create %APP_NAME%

echo.
echo Setting environment variables...
set /p ACCESS_TOKEN="Enter CHANNEL_ACCESS_TOKEN: "
set /p SECRET="Enter CHANNEL_SECRET: "

heroku config:set CHANNEL_ACCESS_TOKEN="%ACCESS_TOKEN%"
heroku config:set CHANNEL_SECRET="%SECRET%"

echo.
echo Adding Heroku remote...
heroku git:remote -a %APP_NAME%

echo.
echo Deploying to Heroku...
git push heroku main

echo.
echo ========================================
echo Deployment Complete!
echo ========================================
echo.
echo Your bot URL: https://%APP_NAME%.herokuapp.com
echo Webhook URL: https://%APP_NAME%.herokuapp.com/callback
echo Test scraping: https://%APP_NAME%.herokuapp.com/test-scraping
echo.
echo Next steps:
echo 1. Go to Line Developer Console
echo 2. Set webhook URL: https://%APP_NAME%.herokuapp.com/callback
echo 3. Enable webhook
echo 4. Test your bot!
echo.
pause