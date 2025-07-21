# # -------------------------------------cell 1--------------------------------------------
# # !pip install bitsandbytes
# # !pip uninstall fitz -y
# # !pip install PyMuPDF
# # !pip install -q "transformers[torch]" pymupdf pillow pandas openpyxl
# # !pip install ipywidgets

# # -------------------------------------cell 2--------------------------------------------
# from huggingface_hub import notebook_login

# # Log in to the Hugging Face Hub
# notebook_login()

# # -------------------------------------cell 3--------------------------------------------
# from transformers import pipeline

# pipe = pipeline(
#     "image-text-to-text",
#     model="unsloth/gemma-3-4b-it-bnb-4bit",
#     model_kwargs={"torch_dtype": "auto"},
#     device_map="auto"
# )

# # ----------------------------------------cell 4-------------------------------------------
# import fitz  # PyMuPDF
# import base64
# from PIL import Image
# from io import BytesIO
# import os

# # Convert PDF to base64 image list
# def pdf_to_images_base64(pdf_path):
#     doc = fitz.open(pdf_path)
#     images_base64 = []
#     for page in doc:
#         pix = page.get_pixmap(dpi=200)
#         img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
#         buffered = BytesIO()
#         img.save(buffered, format="JPEG")
#         encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
#         images_base64.append(encoded)
#     return images_base64

# # Prompt-based extraction from each page
# def run_pdf_vision_prompt(pipe, pdf_path, question, system_prompt="You are a helpful assistant.", max_tokens=300):
#     base64_images = pdf_to_images_base64(pdf_path)
#     responses = []

#     for i, image_b64 in enumerate(base64_images):
#         messages = [
#             {
#                 "role": "system",
#                 "content": [{"type": "text", "text": system_prompt}]
#             },
#             {
#                 "role": "user",
#                 "content": [
#                     {"type": "image", "image": f"data:image/jpeg;base64,{image_b64}"},
#                     {"type": "text", "text": question}
#                 ]
#             }
#         ]
#         output = pipe(text=messages, max_new_tokens=max_tokens)
#         response_text = output[0]["generated_text"][-1]["content"]
#         responses.append((f"Page {i+1}", response_text))

#     return responses

# # ----------------------------------------------cell 5-------------------------------------------
# from google.colab import files
# import time
# import pandas as pd

# # Define PII types dictionary
# pii_dict = {
#     "Aadhar Card Number": "Indian Aadhar Card", "ABA Routing": "", "ABN": "", "ACN": "",
#     "AIR QUALITY PROGRAM OPERATING PERMIT": "", "Alien Registration Number": "", "Bank Account Number": "",
#     "BIC": "", "Branch Code": "", "Branch transit number": "", "BSB": "",
#     "CIN": "Corporate Identification Number (CIN)", "Claim Number": "", "Contact Number": "",
#     "CPT code(s)": "", "Credit Card CVC Code": "", "Credit Card Expiry Date": "", "Credit Card Number": "",
#     "Credit Card Type": "Visa,MasterCard, American Express etc.", "Customer Number": "",
#     "DL Expiry Date": "", "DL Issuance Date": "", "DL Number": "Driving License Number",
#     "DOB": "Date Of Birth", "Docket Number": "", "DOD": "Date Of Death", "DON": "",
#     "Employer Identification Number (EIN)": "", "Expiry date": "", "Facility EPA": "", "FEIN": "",
#     "Group Policy Number": "", "GST Number": "Indian GST Number", "IBAN": "", "Identification No": "",
#     "IFSC": "IFSC (Indian Financial System Code)", "License Number": "", "Loan Number": "",
#     "MICR Code": "MICR Code", "Pan Card  Number": "Indian Permanent Account Number",
#     "Passport Card DOExpiry": "USA Passport Card Number Date Of Expiry", "Passport Card DOIssue": "USA Passport Card Number Date Of Issue",
#     "Passport Card Number": "USA Passport Card Number", "Passport DOExpiry": "USA Passport Date Of Expiry",
#     "Passport DOIssue": "USA Passport Date Of Issue", "Passport Number": "", "Permit Number": "",
#     "Phone/Mobile No.": "Phone Number (Mobile & Landline)", "Pin Code": "Pin Code",
#     "Planned admission date": "", "Policy Effective date": "", "Policy Number": "", "Policy Termination Date": "",
#     "Routing Number": "", "SIN": "Canada Social Insurance Number", "SSN": "Social Security Number",
#     "Swift Code": "", "Tax ID": "", "Tax invoice Number": "", "TFN": "",
#     "TIN": "Tax Identification Number", "TIN Registration No": "India TIN Registration No",
#     "UK NINO": "National Identification Number", "VAT registration number": "",
#     "Vehicle Identification Number": "", "Vehicle License number": "", "VRN": "Indian Vehicle Registration Numbers"
# }

# # Upload and extract
# start_time = time.time()

# uploaded = files.upload()
# pdf_path = next(iter(uploaded))

# # Define the dynamic prompt from PII keys
# pii_list = list(pii_dict.keys())
# question = f"Extract only the following PII types from this document: {', '.join(pii_list)}. For each, provide: PII Type, PII Value, Pre-context, Post-context, and any relevant comment."

# responses = run_pdf_vision_prompt(pipe, pdf_path, question)

# # Prepare structured output
# records = []
# for page, reply in responses:
#     for pii in pii_list:
#         if pii.lower() in reply.lower():
#             # Simplified extraction (parsing improvement needed later)
#             records.append({
#                 "filename": pdf_path,
#                 "country_specific_name": "Unknown",  # Could add detection logic
#                 "path": "forms",
#                 "PII_type": pii,
#                 "PII_value": "<value-extracted>",
#                 "Positve/Negative_example": "Positive",
#                 "Pre-context": "<pre-context>",
#                 "Post-context": "<post-context>",
#                 "General-context": "General",
#                 "Comments": "<comment or blank>"
#             })

# # Save to Excel
# excel_output = pd.DataFrame(records)
# output_filename = "extracted_pii_results.xlsx"
# excel_output.to_excel(output_filename, index=False)

# end_time = time.time()
# print(f"\nExecution Time: {end_time - start_time:.2f} seconds")
# print(f"\nExtracted data saved to {output_filename}")
