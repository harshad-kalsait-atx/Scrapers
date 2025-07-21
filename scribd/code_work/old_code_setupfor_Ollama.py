# import os
# import base64
# import requests
# import shutil

# # Settings
# INPUT_FOLDER = "C:\\Users\\Admin\\Downloads\\dummy_docs"
# PII_FOLDER = "C:\\Users\\Admin\\Downloads\\pii_detected"
# OLLAMA_MODEL = "gemma3:4b"
# PROMPT = "Does this image contain any PII (Personally Identifiable Information) like names, IDs, phone numbers, or addresses? Reply only 'yes' or 'no'."

# # Ensure PII folder exists
# os.makedirs(PII_FOLDER, exist_ok=True)

# # Check all images in input folder
# for filename in os.listdir(INPUT_FOLDER):
#     if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp")):
#         continue

#     image_path = os.path.join(INPUT_FOLDER, filename)
#     print(f"Processing: {filename}")

#     # Encode image to base64
#     with open(image_path, "rb") as f:
#         b64_image = base64.b64encode(f.read()).decode("utf-8")

#     # Send request to Ollama
#     response = requests.post(
#         "http://localhost:11434/api/generate",
#         json={
#             "model": OLLAMA_MODEL,
#             "prompt": PROMPT,
#             "images": [b64_image],
#             "stream": False
#         }
#     )

#     try:
#         result = response.json()
#         answer = result.get("response", "").strip().lower()
#         print("Model response:", answer)

#         # Move image if response is 'yes'
#         if "yes" in answer:
#             shutil.move(image_path, os.path.join(PII_FOLDER, filename))
#             print(f"→ Moved to {PII_FOLDER}")
#         else:
#             print("→ No PII detected")
#     except Exception as e:
#         print("Error:", e)
#         print("Response:", response.text)
 