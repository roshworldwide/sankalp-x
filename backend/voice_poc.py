import boto3
import json
import time
import urllib.request
from dotenv import load_dotenv

load_dotenv()

def engineer_voice_pipeline(audio_path, s3_bucket=None):
    print("Initiating Sankalp X Voice Pipeline...")
    
    try:
        transcribe_client = boto3.client('transcribe')
        s3_client = boto3.client('s3')
        bedrock_client = boto3.client('bedrock-runtime')
        polly_client = boto3.client('polly')
    except Exception as e:
        print(f"Failed to initialize AWS clients: {e}")
        return
        
    print(f"\n[1] EARS: Processing audio: {audio_path}")
    transcribed_text = ""
    
    if s3_bucket:
        try:
            job_name = f"sankalp-x-voice-poc-{int(time.time())}"
            s3_key = f"uploads/{job_name}.wav"
            s3_uri = f"s3://{s3_bucket}/{s3_key}"
            
            print(f"Uploading {audio_path} to {s3_uri}...")
            s3_client.upload_file(audio_path, s3_bucket, s3_key)
            
            print("Starting transcription job...")
            transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': s3_uri},
                MediaFormat='wav',
                LanguageCode='en-IN'
            )
            
            print("Polling transcription job status...")
            while True:
                status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
                job_status = status['TranscriptionJob']['TranscriptionJobStatus']
                if job_status in ['COMPLETED', 'FAILED']:
                    break
                print(f"Job status: {job_status}. Waiting...")
                time.sleep(5)
                
            if job_status == 'COMPLETED':
                transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
                with urllib.request.urlopen(transcript_uri) as response:
                    data = json.loads(response.read())
                    transcribed_text = data['results']['transcripts'][0]['transcript']
                print("Transcription successful.")
            else:
                print("Transcription failed.")
                return
        except FileNotFoundError:
            print(f"Error: Audio file not found at path '{audio_path}'.")
            return
        except Exception as e:
            print(f"Error during Transcribe orchestration: {e}")
            return
    else:
        print("[Mock Bypass] S3 Bucket not provided. Simulating Transcribe output...")
        transcribed_text = "What is the Pradhan Mantri Kisan Samman Nidhi Yojana and how can it help me?"
        
    print(f"Transcribed Input: \"{transcribed_text}\"")
        
    
    print("\n[2] BRAIN: Routing transcribed query to Amazon Nova Premier...")
    
    prompt = f"""
    You are Sankalp X, a helpful Indian government AI assistant designed to aid citizens.
    The user has asked the following query:
    "{transcribed_text}"
    
    Provide a short, welcoming, 2-sentence explanation of a generic agricultural subsidy that answers their query.
    Do not use any formatting (no bolding, italics, or lists). Output plain text only.
    """
    
    cognitive_response_text = ""
    try:
        bedrock_response = bedrock_client.converse(
            modelId="us.amazon.nova-premier-v1:0",
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ],
            inferenceConfig={
                "maxTokens": 300
            }
        )
        
        cognitive_response_text = bedrock_response['output']['message']['content'][0]['text']
        
        print("Cognitive Output generated:")
        print(f"\"{cognitive_response_text}\"")
        
    except Exception as e:
        print(f"Error during Bedrock invocation: {e}")
        return
        
    print("\n[3] MOUTH: Synthesizing speech via Amazon Polly...")
    output_audio_path = "sankalp_response.mp3"
    try:
        polly_response = polly_client.synthesize_speech(
            Text=cognitive_response_text,
            OutputFormat='mp3',
            VoiceId='Kajal',
            Engine='neural'
        )
        
        if 'AudioStream' in polly_response:
            with open(output_audio_path, 'wb') as file:
                file.write(polly_response['AudioStream'].read())
            print(f"Speech synthesis successful! Audio saved to '{output_audio_path}'.")
        else:
            print("Failed to stream audio from Amazon Polly.")
            
    except Exception as e:
        print(f"Error during Polly synthesis: {e}")
        return

if __name__ == "__main__":
    engineer_voice_pipeline("dummy_audio.wav")
    print("\nSankalp X Voice Pipeline prototype execution completed.")
