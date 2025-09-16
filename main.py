import datetime
import uuid
import sys
import logging
import os
import json
from dotenv import load_dotenv
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from aws_secret_util import get_media_server_config, SecretsManagerError

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException, Security, Depends
    from fastapi.security.api_key import APIKeyHeader
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel

    from livekit.api import (
        AccessToken,
        RoomAgentDispatch,
        RoomConfiguration,
        VideoGrants,
    )
    from livekit import api
    from livekit.api import CreateRoomRequest
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Please make sure all required packages are installed: pip install -r requirements.txt")
    sys.exit(1)

app = FastAPI(title="Media Server Token Server")


# Load configuration from AWS Secrets Manager
try:
    # You can configure these via environment variables
    SECRET_NAME = os.getenv("AWS_SECRET_NAME", "asr-media-server-config")
    AWS_REGION = os.getenv("CUSTOM_AWS_REGION", "ap-southeast-1")
    
    logger.info(f"Loading configuration from AWS Secrets Manager: {SECRET_NAME}")
    config = get_media_server_config(SECRET_NAME, AWS_REGION)
    
    MEDIA_SERVER_URL = config['MEDIA_SERVER_URL']
    MEDIA_SERVER_API_KEY = config['MEDIA_SERVER_API_KEY']
    MEDIA_SERVER_API_SECRET = config['MEDIA_SERVER_API_SECRET']
    SECRET_KEYS = config['SECRET_KEYS'].split(",")
    
    logger.info("Successfully loaded configuration from AWS Secrets Manager")
    
except SecretsManagerError as e:
    logger.error(f"Failed to load configuration from AWS Secrets Manager: {e}")
    logger.info("Falling back to environment variables")
    
    # Fallback to environment variables
    MEDIA_SERVER_URL = os.getenv("MEDIA_SERVER_URL")
    MEDIA_SERVER_API_KEY = os.getenv("MEDIA_SERVER_API_KEY")
    MEDIA_SERVER_API_SECRET = os.getenv("MEDIA_SERVER_API_SECRET")
    SECRET_KEYS_ENV = os.getenv("SECRET_KEYS")
    SECRET_KEYS = SECRET_KEYS_ENV.split(",") if SECRET_KEYS_ENV else []
    
except Exception as e:
    logger.error(f"Unexpected error loading configuration: {e}")
    logger.info("Falling back to environment variables")
    
    # Fallback to environment variables
    MEDIA_SERVER_URL = os.getenv("MEDIA_SERVER_URL")
    MEDIA_SERVER_API_KEY = os.getenv("MEDIA_SERVER_API_KEY")
    MEDIA_SERVER_API_SECRET = os.getenv("MEDIA_SERVER_API_SECRET")
    SECRET_KEYS_ENV = os.getenv("SECRET_KEYS")
    SECRET_KEYS = SECRET_KEYS_ENV.split(",") if SECRET_KEYS_ENV else []



class TokenResponse(BaseModel):
    token: str
    room_name: str
    participant: str
    agent: str


class CustomerInfo(BaseModel):
    name: str
    email: str

class TokenRequest(BaseModel):
    customer: Optional[CustomerInfo] = None
    agent_name: str = "ivy"

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# dynamodb = boto3.resource('dynamodb',
#     region_name=os.getenv('CUSTOM_AWS_REGION', 'ap-southeast-1')
# )

# USER_TABLE_NAME = os.getenv('DYNAMODB_USER_TABLE', 'UserAgent')


async def get_api_key(api_key_header: Optional[str] = Security(api_key_header)):
    """Validate the API key in the request header."""
    if api_key_header is None:
        logger.warning("API key missing in request")
        raise HTTPException(
            status_code=403, 
            detail="API key is missing in the request header"
        )

    if api_key_header in SECRET_KEYS:
        return SECRET_KEYS.index(api_key_header) + 1
    
    logger.warning("Invalid API key provided")
    raise HTTPException(
        status_code=403, 
        detail="Invalid API key"
    )
        

@app.post("/token", response_model=TokenResponse, dependencies=[Depends(get_api_key)])
async def get_token(request: TokenRequest, user_id: int = Depends(get_api_key)):
    """Generate a Media Server token with agent dispatch configuration."""
    try:
        if not all([MEDIA_SERVER_URL, MEDIA_SERVER_API_KEY, MEDIA_SERVER_API_SECRET]):
            logger.error("Missing required environment variables")
            raise HTTPException(
                status_code=500, 
                detail="Server configuration error: Missing Media Server credentials"
            )
        
        random_chars = uuid.uuid4().hex[:6]
        participant_identity = f"identity-{random_chars}"
        random_chars = uuid.uuid4().hex
        room_name = f"web-call-{random_chars}"
        # l = api.LiveKitAPI(MEDIA_SERVER_URL, MEDIA_SERVER_API_KEY, MEDIA_SERVER_API_SECRET)
        
        # Build metadata with optional customer info
        metadata = {
            "agent": request.agent_name,
            "user_id": user_id
        }
        if request.customer:
            metadata["customer"] = {
                "name": request.customer.name,
                "email": request.customer.email
            }
        
        token = (
            AccessToken(MEDIA_SERVER_API_KEY, MEDIA_SERVER_API_SECRET)
            .with_identity(participant_identity)
            .with_grants(VideoGrants(room_join=True, room=room_name))
            .with_ttl(datetime.timedelta(hours=24))  
            .with_room_config(
                RoomConfiguration(
                    agents=[
                        RoomAgentDispatch(agent_name="k-a", metadata=json.dumps(metadata))
                    ],
                ),
            )
            .to_jwt()
        )
        print(token)
        return {"token": token, "room_name": room_name, "participant": participant_identity, "agent": request.agent_name}
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating token: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint that returns a welcome message."""
    return {"message": "Welcome to Media Server Token Server. Use /token endpoint to generate a token."}


if __name__ == "__main__":
    try:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except ImportError:
        logger.error("Uvicorn not found. Please install it with: pip install uvicorn")
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")