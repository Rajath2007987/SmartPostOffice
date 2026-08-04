# Deployment Guide for Smart Post Office App

This guide provides instructions to deploy the Flask application to different platforms: Heroku, AWS Elastic Beanstalk, and Render.

## Prerequisites

- Python 3.9+
- Git
- Accounts on the respective platforms (Heroku, AWS, Render)

## Environment Variables

Before deploying, set the following environment variables in your deployment platform:

- `SECRET_KEY`: A secret key for Flask sessions
- `ADMIN_USERNAME`: Admin username (default: admin)
- `ADMIN_PASSWORD`: Admin password (default: admin123)
- `MAIL_SERVER`: SMTP server for email
- `MAIL_PORT`: SMTP port
- `MAIL_USE_TLS`: True for TLS
- `MAIL_USERNAME`: SMTP username
- `MAIL_PASSWORD`: SMTP password
- `MAIL_DEFAULT_SENDER`: Default sender email
- `TWILIO_ACCOUNT_SID`: Twilio account SID
- `TWILIO_AUTH_TOKEN`: Twilio auth token
- `TWILIO_PHONE_NUMBER`: Twilio phone number
- `RAZORPAY_KEY_ID`: Razorpay key ID
- `RAZORPAY_KEY_SECRET`: Razorpay key secret
- `PUBLIC_BASE_URL`: Public base URL for QR codes (optional)

## Deployment Options

### 1. Heroku

Heroku offers a free tier suitable for students.

1. Run the `heroku_deploy.bat` script.
2. Follow the prompts to install CLI, login, and deploy.
3. Your app will be accessible at `https://your-app-name.herokuapp.com`

### 2. AWS Elastic Beanstalk

AWS provides a free tier for 12 months.

1. Run the `aws_deploy.bat` script.
2. Follow the prompts to install CLIs, configure AWS, and deploy.
3. Your app will be accessible at the EB environment URL.

### 3. Render

Render offers a free tier with 750 hours/month.

1. Push your code to a GitHub repository.
2. Run the `render_deploy.bat` script or use the web dashboard.
3. Create a new Web Service from your GitHub repo.
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `gunicorn wsgi:app`
6. Your app will be accessible at the Render URL.

## Notes

- The app uses SQLite, which is file-based. For production, consider using a persistent database like PostgreSQL.
- Update the `PUBLIC_BASE_URL` environment variable with your deployed app's URL for QR codes to work properly.
- Monitor your free tier usage to avoid unexpected charges.

## Local Testing

To test locally before deploying:

```bash
pip install -r requirements.txt
python app.py
```

Visit `http://127.0.0.1:5000`
