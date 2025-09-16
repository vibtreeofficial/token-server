import os
import json
from mangum import Mangum
from main import app

# Create Mangum handler for AWS Lambda
handler = Mangum(app)
