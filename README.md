# Token Server

A FastAPI server that generates Server tokens with agent dispatch configuration. This server can be run locally or deployed to AWS Lambda, with API key authentication using AWS Secret Manager.

## Features

- Single endpoint (`/token`) to generate media server tokens
- Automatic room creation with each token
- Agent dispatch configuration included in the token
- API Key authentication via DynamoDB
- AWS Lambda deployment support via Serverless Framework

## Architecture

- **Backend**: FastAPI (Python)
- **Deployment**: AWS Lambda + API Gateway + Secrets Manager via Serverless Framework
- **Authentication**: API Key validation against AWS Secret Manager

## Requirements

- Python 3.9+
- Node.js and npm (for Serverless Framework)
- AWS account with configured credentials
- AWS Secret Manager with media server configuration


## Local Development Setup

1. **Clone the repository**

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file**:
   Copy `.env.example` to `.env` and fill in your configuration values:
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

5. **Run the server locally**:
   ```bash
   uvicorn main:app --reload
   ```

6. **Test the API**:
   ```bash
   curl -X GET http://localhost:8000/token -H "X-API-Key: your_api_key_here"
   ```

## AWS Lambda Deployment

### Prerequisites

1. **Install Node.js dependencies**:
   ```bash
   npm install
   ```

2. **Configure AWS credentials** (if not already done):
   ```bash
   aws configure
   ```

### Deployment Steps

1. **Update environment variables**:
   Make sure your `.env` file contains all required variables. Note that `AWS_REGION` is a reserved variable in Lambda, so we use `CUSTOM_AWS_REGION` instead.

2. **Deploy to AWS Lambda**:
   ```bash
   npx serverless deploy
   ```

3. **Note the API Gateway endpoint URL** from the deployment output.

### Troubleshooting Deployment

- If you encounter Docker-related issues, you can disable Docker in `serverless.yml`:
  ```yaml
  custom:
    pythonRequirements:
      dockerizePip: false
  ```

- For permission issues, ensure your AWS user has the necessary IAM permissions for Lambda, API Gateway, CloudFormation, and DynamoDB.

## Environment Variables for local testing

| Variable | Description | Required |
|----------|-------------|----------|
| `MEDIA_SERVER_URL` | URL of your Media server | Yes |
| `SERVER_API_KEY` | Your Media Server API key | Yes |
| `SERVER_API_SECRET` | Your Media Server API secret | Yes |
| `AGENT_NAME` | Default agent name | Yes |
| `CUSTOM_AWS_REGION` | AWS region for DynamoDB | Yes |
| `AWS_ACCESS_KEY_ID` | AWS access key ID | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | Yes |
| `DYNAMODB_USER_TABLE` | Name of your DynamoDB table | Yes |

## API Endpoints

### GET /

Returns a welcome message.

### POST /token

Generates a Media Server token with agent dispatch configuration.

**Headers**:
- `X-API-Key`: Your API key (required)

**Response**:
```json
{
  "token": "your_jwt_token_here",
  "room_name": "web-call-abc123",
  "participant": "identity-abc123",
  "agent": "ivy"
}
```

## Project Structure

- `main.py`: Main FastAPI application
- `lambda_handler.py`: AWS Lambda handler using Mangum
- `serverless.yml`: Serverless Framework configuration
- `requirements.txt`: Python dependencies
- `.env.example`: Example environment variables
- `.gitignore`: Git ignore patterns
- `aws_secret_manager.py`: AWS Secret Manager configuration