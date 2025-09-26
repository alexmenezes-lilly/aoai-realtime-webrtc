from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv
import requests
from openai import AzureOpenAI

load_dotenv()

app = Flask(__name__)
CORS(app)

AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_CHAT_ENDPOINT = os.getenv('AZURE_OPENAI_CHAT_ENDPOINT')
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME = os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT_NAME')
AZURE_OPENAI_CHAT_APIVERSION = "2024-12-01-preview"
AZURE_OPENAI_REALTIME_ENDPOINT = os.getenv('AZURE_OPENAI_REALTIME_ENDPOINT')
AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME = os.getenv('AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME')
AZURE_OPENAI_REALTIME_WEBRTC_ENDPOINT = os.getenv('AZURE_OPENAI_REALTIME_WEBRTC_ENDPOINT')


@app.route('/api/ephemeral-key', methods=['POST'])
def generate_ephemeral_key():
    try:
        # Generate ephemeral key using Azure OpenAI API
        headers = {
            'api-key': AZURE_OPENAI_API_KEY,
            'Content-Type': 'application/json',            
        }        
        data = {
            'model': AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME,
            'voice': 'alloy',  # Example voice parameter
            'input_audio_noise_reduction': {
                'type': 'near_field'
            },  # Example noise reduction parameter
        }
        
        url = f"{AZURE_OPENAI_CHAT_ENDPOINT}/openai/realtimeapi/sessions?api-version=2025-04-01-preview"
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            print("Realtime API Response:", response.json())
            data = response.json()
            return jsonify({
                'token': data["client_secret"]["value"],
                'endpoint': AZURE_OPENAI_REALTIME_WEBRTC_ENDPOINT,                
            })
        else:
            print("Error Response:", response.status_code, response.text)
            return jsonify({'error': 'Failed to contact the Realtime API'}), 500
            
    except Exception as e:
        print("Exception:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/webrtc-session', methods=['POST'])
def create_webrtc_session():
    try:
        # Get the SDP offer from the frontend
        data = request.get_json()
        sdp_offer = data.get('sdp')
        ephemeral_key = data.get('token')

        print(f"Received SDP offer length: {len(sdp_offer) if sdp_offer else 0}")
        print(f"Ephemeral key: {ephemeral_key[:20]}..." if ephemeral_key else "No key")
                
        if not sdp_offer or not ephemeral_key:
            return jsonify({'error': 'Missing SDP offer or ephemeral key'}), 400
        
        # Forward the request to Azure OpenAI Realtime API
        headers = {
            'Authorization': f'Bearer {ephemeral_key}',
            'Content-Type': 'application/sdp'
        }
        
        response = requests.post(
            AZURE_OPENAI_REALTIME_WEBRTC_ENDPOINT,
            headers=headers,
            data=sdp_offer
        )
        
        if response.ok:
            return response.text, 200, {'Content-Type': 'application/sdp'}
        else:
            print("WebRTC Session Error:", response.status_code, response.text)
            return jsonify({'error': 'Failed to create WebRTC session'}), response.status_code
            
    except Exception as e:
        print("Exception in WebRTC session:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/send-question', methods=['POST'])
def send_question():
    try:
        # Get the question text from the request
        data = request.get_json()
        question_text = data.get('text')
        
        if not question_text:
            return jsonify({'error': 'Missing question text'}), 400
        
        # Initialize Azure OpenAI client
        client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_CHAT_APIVERSION,
            azure_endpoint=AZURE_OPENAI_CHAT_ENDPOINT
        )
        
        # Make chat completion request
        response = client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
            messages=[
                {
                    'role': 'system', 
                    'content': 'You are a helpful assistant that translates text from English to Brazilian Portuguese.'
                },
                {
                    'role': 'user',
                    'content': question_text
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        answer = response.choices[0].message.content
        print("Chat Completion Response:", response)

        usage = {
            'prompt_tokens': response.usage.prompt_tokens,
            'completion_tokens': response.usage.completion_tokens,
            'total_tokens': response.usage.total_tokens
        }
        
        return jsonify({
            'answer': answer,
            'usage': usage
        })
            
    except Exception as e:
        print("Exception in send_question:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
