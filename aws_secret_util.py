import json
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class SecretsManagerError(Exception):
    """Custom exception for Secrets Manager related errors."""
    pass


def get_secret(secret_name: str, region_name: str = "us-east-1") -> Dict[str, Any]:
    """
    Retrieve a secret from AWS Secrets Manager.
    
    Args:
        secret_name (str): The name or ARN of the secret to retrieve
        region_name (str): AWS region where the secret is stored (default: us-east-1)
    
    Returns:
        Dict[str, Any]: The secret values as a dictionary
    
    Raises:
        SecretsManagerError: If there's an error retrieving the secret
    """
    try:
        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
        
        logger.info(f"Attempting to retrieve secret: {secret_name} from region: {region_name}")
        
        # Retrieve the secret value
        response = client.get_secret_value(SecretId=secret_name)
        
        # Parse the secret string as JSON
        secret_string = response['SecretString']
        secret_dict = json.loads(secret_string)
        
        logger.info(f"Successfully retrieved secret: {secret_name}")
        return secret_dict
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'DecryptionFailureException':
            logger.error(f"Secrets Manager can't decrypt the protected secret text using the provided KMS key: {error_message}")
            raise SecretsManagerError(f"Failed to decrypt secret '{secret_name}': {error_message}")
        elif error_code == 'InternalServiceErrorException':
            logger.error(f"An error occurred on the server side: {error_message}")
            raise SecretsManagerError(f"Internal service error while retrieving secret '{secret_name}': {error_message}")
        elif error_code == 'InvalidParameterException':
            logger.error(f"Invalid parameter provided: {error_message}")
            raise SecretsManagerError(f"Invalid parameter for secret '{secret_name}': {error_message}")
        elif error_code == 'InvalidRequestException':
            logger.error(f"Invalid request: {error_message}")
            raise SecretsManagerError(f"Invalid request for secret '{secret_name}': {error_message}")
        elif error_code == 'ResourceNotFoundException':
            logger.error(f"Secret not found: {error_message}")
            raise SecretsManagerError(f"Secret '{secret_name}' not found: {error_message}")
        else:
            logger.error(f"Unexpected AWS error: {error_code} - {error_message}")
            raise SecretsManagerError(f"AWS error retrieving secret '{secret_name}': {error_code} - {error_message}")
            
    except NoCredentialsError:
        logger.error("AWS credentials not found")
        raise SecretsManagerError("AWS credentials not found. Please configure your AWS credentials.")
        
    except PartialCredentialsError:
        logger.error("Incomplete AWS credentials")
        raise SecretsManagerError("Incomplete AWS credentials. Please check your AWS configuration.")
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse secret as JSON: {e}")
        raise SecretsManagerError(f"Secret '{secret_name}' is not valid JSON: {e}")
        
    except Exception as e:
        logger.error(f"Unexpected error retrieving secret: {e}")
        raise SecretsManagerError(f"Unexpected error retrieving secret '{secret_name}': {e}")


def get_media_server_config(secret_name: str, region_name: str = "ap-southeast-1") -> Dict[str, str]:
    """
    Retrieve media server configuration from AWS Secrets Manager.
    
    Expected secret format:
    {
        "MEDIA_SERVER_URL": "wss://your-server.com",
        "MEDIA_SERVER_API_KEY": "your-api-key",
        "MEDIA_SERVER_API_SECRET": "your-api-secret",
        "SECRET_KEYS": "key1,key2,key3"
    }
    
    Args:
        secret_name (str): The name of the secret containing media server config
        region_name (str): AWS region where the secret is stored
    
    Returns:
        Dict[str, str]: Configuration values with keys:
            - MEDIA_SERVER_URL
            - MEDIA_SERVER_API_KEY  
            - MEDIA_SERVER_API_SECRET
            - SECRET_KEYS (comma-separated string)
    
    Raises:
        SecretsManagerError: If there's an error retrieving the secret or missing required keys
    """
    try:
        secret_dict = get_secret(secret_name, region_name)
        
        # Validate required keys
        required_keys = ['MEDIA_SERVER_URL', 'MEDIA_SERVER_API_KEY', 'MEDIA_SERVER_API_SECRET', 'SECRET_KEYS']
        missing_keys = [key for key in required_keys if key not in secret_dict]
        
        if missing_keys:
            logger.error(f"Missing required keys in secret '{secret_name}': {missing_keys}")
            raise SecretsManagerError(f"Secret '{secret_name}' is missing required keys: {missing_keys}")
        
        logger.info("Successfully retrieved and validated media server configuration")
        return {
            'MEDIA_SERVER_URL': secret_dict['MEDIA_SERVER_URL'],
            'MEDIA_SERVER_API_KEY': secret_dict['MEDIA_SERVER_API_KEY'],
            'MEDIA_SERVER_API_SECRET': secret_dict['MEDIA_SERVER_API_SECRET'],
            'SECRET_KEYS': secret_dict['SECRET_KEYS']
        }
        
    except SecretsManagerError:
        # Re-raise SecretsManagerError as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_media_server_config: {e}")
        raise SecretsManagerError(f"Failed to get media server config: {e}")