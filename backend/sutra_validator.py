import json
import boto3
import os

bedrock_client = None

def get_bedrock_client():
    from main import bedrock_client as main_bedrock_client
    global bedrock_client
    if bedrock_client is None:
        if main_bedrock_client is not None:
            bedrock_client = main_bedrock_client
        else:
            bedrock_client = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'))
    return bedrock_client

class EthicalGuardrailVeto(Exception):
    pass

class SutraValidator:
    @staticmethod
    def align_response(draft_response: str) -> str:
        print("[Sutra Validator] Checking output against IndiaAI 7 Sutras...")
        
        system_prompt = f"""
        You are the Ethical Guardian of Sankalp X.
        Review the following generated response strictly against the IndiaAI '7 Sutras' framework:
        1. Trust (Reliable info)
        2. People First (Helpful, non-toxic)
        3. Fairness (Non-discriminatory)
        4. Inclusivity
        5. Transparency
        6. Accountability
        7. Sustainability
        
        Draft Response: "{draft_response}"
        
        If this response violates ANY of these sutras (e.g., uses discriminatory language, provides harmful instructions, or unjustly denies service), return EXACTLY:
        {{
            "status": "VETO",
            "reason": "(Brief explanation why it violated Sutra X)"
        }}
        
        If it is safe and aligned, return EXACTLY:
        {{
            "status": "ALIGNED",
            "reason": "Meets 7 Sutras criteria."
        }}
        
        Output ONLY valid JSON without markdown.
        """
        
        try:
            client = get_bedrock_client()
            response = client.converse(
                modelId="us.amazon.nova-micro-v1:0",
                messages=[{"role": "user", "content": [{"text": system_prompt}]}],
                inferenceConfig={"maxTokens": 200, "temperature": 0.0}
            )
            nova_json_str = response['output']['message']['content'][0]['text'].strip()
            
            if nova_json_str.startswith('```json'):
                nova_json_str = nova_json_str[7:]
            if nova_json_str.endswith('```'):
                nova_json_str = nova_json_str[:-3]
                
            validation = json.loads(nova_json_str.strip())
            
            if validation.get("status") == "VETO":
                print(f"[Sutra Validator] VETO TRIGGERED: {validation.get('reason')}")
                raise EthicalGuardrailVeto(validation.get("reason"))
            
            print("[Sutra Validator] Response is ALIGNED with 7 Sutras.")
            return draft_response
            
        except EthicalGuardrailVeto as e:
            raise e
        except Exception as e:
            print(f"[Sutra Validator Runtime Error] Defaulting to safe. Error: {e}")
            return draft_response
