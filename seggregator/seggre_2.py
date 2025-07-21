# This script processes images and PDFs to detect PII using the Ollama model which is running on a Colab instance.
# It requires an active ngrok tunnel to communicate with the Ollama API.
# Make sure to run this script in an environment where the Ollama model is accessible via the provided ngrok URL.

import os
import base64
import time
import requests
import shutil
import fitz  # PyMuPDF
from pdf2image import convert_from_path
from PIL import Image

# === Settings ===
INPUT_FOLDER = "folder_with_forms"  # Make sure this path exists on your local machine
PII_FOLDER = "Empty_forms"  # Folder to move files with PII
OLLAMA_MODEL = "gemma3:4b"
PROMPT = "Is this document a form or contains a form structure (like labeled fields, blanks to fill in, checkboxes, or signature areas)? Reply only 'yes' or 'no'."
# "Does this contain any PII (Personally Identifiable Information) like names, IDs, phone numbers, or addresses? Reply only 'yes' or 'no'."
# "Is this document an empty form with labeled blank fields to be filled out? Reply only 'yes' or 'no'."
# !!! IMPORTANT: Replace this with the ngrok public URL from  your Colab output !!!
OLLAMA_API_URL = "https://e0a1e7a563f6.ngrok-free.app/api/generate" # e.g., "https://abcdef123456.ngrok-free.app/api/generate"



# === Ensure Output Folder Exists ===
os.makedirs(PII_FOLDER, exist_ok=True)


# payload = {
#         "model": OLLAMA_MODEL,
#         "prompt": "how are you",
#         "stream": False
#     }

# response = requests.post(OLLAMA_API_URL, json=payload, timeout=300) # Added timeout for potentially slow Colab responses
# print("Test response from Ollama:", response.content)
# exit()

# === Ask Ollama ===
def ask_ollama(prompt_text=None, image_b64=None):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": PROMPT,
        "stream": False
    }
    if image_b64:
        payload["images"] = [image_b64]
    elif prompt_text:
        payload["prompt"] += f"\n\nText:\n{prompt_text[:3000]}"  # Trim large text

    try:
        # Use the dynamically set OLLAMA_API_URL
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=300) # Added timeout for potentially slow Colab responses
        result = response.json()
        return result.get("response", "").strip().lower()
    except requests.exceptions.Timeout:
        print("Error: Ollama request timed out.")
        return "error_timeout"
    except requests.exceptions.RequestException as e:
        print("Error contacting Ollama (via ngrok):", e)
        print(f"Ensure the Colab runtime is active and ngrok tunnel is running. URL used: {OLLAMA_API_URL}")
        return "error_connection"
    except Exception as e:
        print("An unexpected error occurred in ask_ollama:", e)
        return "error_unexpected"
    
# === Handle Images ===
def handle_image(file_path, filename):
    print(f"Processing image: {filename}")
    try:
        with open(file_path, "rb") as f:
            b64_image = base64.b64encode(f.read()).decode("utf-8")
        response = ask_ollama(image_b64=b64_image)
        print("Model response:", response)
        if "yes" in response:
            shutil.move(file_path, os.path.join(PII_FOLDER, filename))
            print(f"→ Moved to {PII_FOLDER}")
        else:
            print("→ No PII detected in image")
    except Exception as e:
        print(f"Error processing image {filename}: {e}")

# === Handle PDFs ===
start_time = time.time()
def handle_pdf(file_path, filename):
    print(f"Processing PDF: {filename}")
    has_text = False
    full_text = ""

    # === Step 1: Try reading text from first 20 pages
    try:
        doc = fitz.open(file_path)
        total_pages = min(len(doc), 20)
        for page_num in range(total_pages):
            page = doc.load_page(page_num)
            page_text = page.get_text().strip()
            if page_text:
                has_text = True
                full_text += page_text + "\n"
        doc.close()

        if has_text:
            print("→ Text detected in PDF, using text-based detection (first 20 pages)")
            response = ask_ollama(prompt_text=full_text)
            print("Model response:", response)
            if "yes" in response:
                shutil.move(file_path, os.path.join(PII_FOLDER, filename))
                print(f"→ Moved to {PII_FOLDER}")
            else:
                print("→ No PII detected in PDF text")
            return

        print("→ No text found, switching to image-based detection (first 20 pages)")

    except Exception as e:
        print(f"Error reading PDF text: {e}")
        # If text extraction fails, still try image conversion
        pass # Continue to image conversion part


    # === Step 2: Convert to image (first 20 pages)
    try:
        images = convert_from_path(file_path, first_page=1, last_page=20)
        for i, img in enumerate(images):
            temp_img_path = "temp_page.jpg"
            img.convert("RGB").save(temp_img_path, "JPEG")

            with open(temp_img_path, "rb") as f:
                b64_image = base64.b64encode(f.read()).decode("utf-8")

            response = ask_ollama(image_b64=b64_image)
            print(f"Page {i+1} response:", response)

            if "yes" in response:
                shutil.move(file_path, os.path.join(PII_FOLDER, filename))
                print(f"→ Moved to {PII_FOLDER}")
                break # Stop processing pages if PII is found

        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

    except Exception as e:
        print(f"Error converting PDF to images: {e}")

# === Walk Through All Subfolders ===
for root, dirs, files in os.walk(INPUT_FOLDER):
    for filename in files:
        file_path = os.path.join(root, filename)
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp")):
            handle_image(file_path, filename)
        elif filename.lower().endswith(".pdf"):
            handle_pdf(file_path, filename)
        else:
            print(f"Skipping unsupported file: {filename}")

# === Summary ===
end_time = time.time()
elapsed_time = end_time - start_time
print(f"Processing completed in {elapsed_time:.2f} seconds.")