# # Cell 1: Install Ollama
# # (Assuming you've already done this, but including for completeness)
# print("--- Installing Ollama ---")
# !curl -fsSL https://ollama.ai/install.sh | sh
# print("Ollama installed.")

# # Set LD_LIBRARY_PATH for NVIDIA GPU if available
# import os
# print("--- Setting LD_LIBRARY_PATH ---")
# os.environ.update({'LD_LIBRARY_PATH': '/usr/lib64-nvidia'})
# print(f"LD_LIBRARY_PATH set to: {os.environ.get('LD_LIBRARY_PATH')}")

# # Cell 2: Start Ollama server in background
# import subprocess
# import time

# print("--- Starting Ollama server ---")
# try:
#     # Using Popen for non-blocking background process
#     # Redirecting stdout/stderr to files to keep Colab output clean
#     with open("ollama_server.log", "w") as outfile, open("ollama_server_err.log", "w") as errfile:
#         ollama_serve_process = subprocess.Popen(
#             ["nohup", "ollama", "serve"],
#             stdout=outfile,
#             stderr=errfile,
#             preexec_fn=os.setsid
#         )
#     print("Ollama server started in the background. Check ollama_server.log for details.")
#     time.sleep(10) # Give Ollama some time to initialize
#     print("Ollama server should be running.")
# except Exception as e:
#     print(f"Error starting Ollama server: {e}")
#     exit()

# # Cell 3: Pull the model (if not already pulled)
# model_name = "gemma3:4b"
# print(f"--- Pulling Ollama model: {model_name} ---")
# try:
#     pull_command = ["ollama", "pull", model_name]
#     pull_result = subprocess.run(pull_command, capture_output=True, text=True, check=True)
#     print(pull_result.stdout)
#     print(pull_result.stderr)
#     print(f"Model '{model_name}' pulled successfully!")
# except subprocess.CalledProcessError as e:
#     print(f"Error pulling model {model_name}: {e}")
#     print(f"Stdout: {e.stdout}")
#     print(f"Stderr: {e.stderr}")
#     # If model pull fails, subsequent steps will also fail, so you might want to exit or handle.


# # Cell 4: Install pyngrok and expose Ollama
# print("--- Setting up ngrok tunnel ---")
# !pip install pyngrok -qq # -qq for quiet installation

# from pyngrok import ngrok
# from google.colab import userdata

# # Retrieve your authtoken from Colab secrets
# NGROK_AUTHTOKEN = userdata.get('NGROK_AUTHTOKEN')
# if not NGROK_AUTHTOKEN:
#     raise ValueError("NGROK_AUTHTOKEN not found in Colab secrets. Please set it.")

# ngrok.set_auth_token(NGROK_AUTHTOKEN)

# # Disconnect any existing tunnels before creating a new one (good practice)
# ngrok.disconnect()

# # Create the tunnel to Ollama's default port (11434)
# # The `host_header` is important for Ollama to correctly route requests
# try:
#     ollama_tunnel = ngrok.connect(11434, host_header="localhost:11434")
#     public_url = ollama_tunnel.public_url
#     print(f"🎉 Ollama tunnel created! You can now access it at: {public_url}")
#     print(f"This URL will be valid as long as this Colab session is active.")

#     # Store the public URL in an environment variable for easier access in other cells
#     os.environ['OLLAMA_HOST'] = public_url

# except Exception as e:
#     print(f"Error creating ngrok tunnel: {e}")
#     print("Make sure your ngrok authtoken is correct and the Ollama server is running.")
#     exit()

# # Cell 5 (Optional): Test from Colab itself using the public URL
# # This verifies the tunnel is working before you try from local machine
# print("\n--- Testing Ollama via public URL from Colab ---")
# import requests
# import json

# test_url = f"{public_url}/api/generate"
# test_payload = {
#     "model": "gemma3:4b",
#     "prompt": "What is 2+2?",
#     "stream": False
# }

# try:
#     response = requests.post(test_url, data=json.dumps(test_payload))
#     if response.status_code == 200:
#         print("✅ Test Response from Ollama via public URL:")
#         print(response.json()["response"])
#     else:
#         print(f"❌ Test Request failed with status code {response.status_code}")
#         print(response.text)
# except requests.exceptions.ConnectionError as e:
#     print(f"❌ Connection error during public URL test: {e}")
#     print("This often means the ngrok tunnel isn't fully established or has dropped.")
# except Exception as e:
#     print(f"An unexpected error occurred during public URL test: {e}")