import boto3
import json
import os
from dotenv import load_dotenv

load_dotenv()

def extract_and_reason(image_path):
    print("Initiating Sankalp X Cognitive Pipeline...")
    
    try:
        textract_client = boto3.client('textract')
        bedrock_client = boto3.client('bedrock-runtime')
    except Exception as e:
        print(f"Failed to initialize AWS clients: {e}")
        return
    
    print(f"Scanning document: {image_path} via Amazon Textract...")
    try:
        with open(image_path, 'rb') as document:
            image_bytes = document.read()
            
        textract_response = textract_client.detect_document_text(
            Document={'Bytes': image_bytes}
        )
        
        lines = [block['Text'] for block in textract_response.get('Blocks', []) if block['BlockType'] == 'LINE']
        extracted_raw_text = " ".join(lines)
        print("Extraction successful.")
        
    except FileNotFoundError:
        print(f"Error: Image file not found at path '{image_path}'.")
        return
    except Exception as e:
        print(f"Error during Textract extraction: {e}")
        return
    
    print("Routing raw data to Claude 3.5 Sonnet for JSON structuring...")
    
    prompt = f"""
    You are the core intelligence of Sankalp X. 
    Take the following raw text extracted from an Aadhaar card and return a strictly formatted JSON object containing 'Name', 'ID_Number', and 'DOB'.
    Output ONLY valid JSON, without any markdown formatting like ```json or ```.
    Raw Text: {extracted_raw_text}
    """
    
    try:
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        bedrock_response = bedrock_client.invoke_model(
            modelId="us.anthropic.claude-sonnet-4-6",
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(bedrock_response['body'].read())
        final_output = response_body['content'][0]['text']
        
        print("Bedrock Processing Complete. Final JSON Output Ready:")
        print(final_output)
        return final_output
        
    except Exception as e:
        print(f"Error during Bedrock invocation: {e}")
        return None

if __name__ == "__main__":
    extract_and_reason("dummy_id.png")
    print("Sankalp X Cognitive Pipeline API implementation loaded.")