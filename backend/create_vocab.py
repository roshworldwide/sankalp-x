import boto3
import time
import os
from dotenv import load_dotenv

# 1. Load your AWS keys from the .env file
load_dotenv()

# 2. Explicitly pass the credentials to Boto3
transcribe = boto3.client(
    'transcribe', 
    region_name=os.getenv('AWS_REGION', 'us-east-1'), # Defaults to us-east-1 if not set
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

vocabulary_name = 'SovereignV_V2'

# Notice the hyphen in Ration-Card! No spaces allowed in AWS API.
phrases = [
    "Ration-Card", "Ombudsman", "Grievance", "MLA", "Verification", 
    "Sovereign", "Aadhaar", "Panchayat", "Tehsildar", "Sankalp"
]

try:
    print(f"Creating Custom Vocabulary: {vocabulary_name}...")
    response = transcribe.create_vocabulary(
        VocabularyName=vocabulary_name,
        LanguageCode='hi-IN',
        Phrases=phrases
    )
    
    while True:
        status = transcribe.get_vocabulary(VocabularyName=vocabulary_name)
        vocab_state = status['VocabularyState']
        if vocab_state in ['READY', 'FAILED']:
            print(f"Vocabulary Status: {vocab_state}")
            break
        print("Waiting for AWS to build the vocabulary... (10s)")
        time.sleep(10)

except Exception as e:
    print(f"Error: {e}")