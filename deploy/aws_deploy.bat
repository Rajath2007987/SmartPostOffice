@echo off
echo Setting up AWS Elastic Beanstalk deployment...

REM Check if AWS CLI is installed
aws --version >nul 2>&1
if %errorlevel% neq 0 (
    echo AWS CLI not found. Installing...
    REM Download and install AWS CLI for Windows
    powershell -Command "Invoke-WebRequest -Uri 'https://awscli.amazonaws.com/AWSCLIV2.msi' -OutFile 'AWSCLIV2.msi'"
    msiexec /i AWSCLIV2.msi /quiet
    echo AWS CLI installed.
) else (
    echo AWS CLI is already installed.
)

REM Check if EB CLI is installed
eb --version >nul 2>&1
if %errorlevel% neq 0 (
    echo EB CLI not found. Installing...
    pip install awsebcli
    echo EB CLI installed.
) else (
    echo EB CLI is already installed.
)

REM Configure AWS CLI (user needs to input credentials)
echo Configuring AWS CLI...
aws configure

REM Initialize EB if not already
if not exist .elasticbeanstalk (
    echo Initializing Elastic Beanstalk...
    eb init your-smart-post-office-app -p python-3.9 -r us-east-1
) else (
    echo Elastic Beanstalk already initialized.
)

REM Create environment
echo Creating EB environment...
eb create smart-post-office-env

REM Set environment variables
eb setenv SECRET_KEY=your-secret-key-change-this ADMIN_USERNAME=admin ADMIN_PASSWORD=admin123
REM Add other env vars as needed

REM Deploy
echo Deploying to AWS EB...
eb deploy

REM Open the app
eb open

echo Deployment complete! Your app is live on AWS Elastic Beanstalk.
pause
