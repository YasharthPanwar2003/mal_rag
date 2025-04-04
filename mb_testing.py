import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import re
import fitz  # PyMuPDF
import json 
import os
import gc
import numpy as np
import pandas as pd
import re
import requests
from transformers.utils import logging
logging.set_verbosity_error()

import json
import embedd as qd

class Malware_Rag:
    # Extract text from the PDF
    def extract_text_from_pdf(self,pdf_name):
        pdf_name = "files/" + pdf_name
        pdf_document = fitz.open(pdf_name)
        all_text = ""
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text = page.get_text("text")
            all_text += text
        return all_text

    #extract hashes from text
    def extract_sha256_hashes(self,text):
        # Define the regular expression pattern for a SHA-256 hash
        pattern = r'\b[a-fA-F0-9]{64}\b'
        
        # Find all matches in the input text
        hashes = re.findall(pattern, text)
        
        # Use a set to get unique hashes
        unique_hashes = set(hashes)
        
        return unique_hashes


    #given the hash number and the output directory, output the json file
    def fetch_json(self,hash_number, output_dir):
        hash_number = hash_number.strip().replace('"', '')  # Clean the hash number
        
        # Replace 'your_api_key_here' with your actual Malware Bazaar API key
        api_key = 'YOUR API KEY'
        headers = {
            'API-KEY': api_key
        }

        url = 'https://mb-api.abuse.ch/api/v1/'

        # Define the payload for querying a specific hash
        payload = {
            'query': 'get_info',
            'hash': hash_number
        }

        try:
            # Make the request
            response = requests.post(url, headers=headers, data=payload, timeout=15)
            
            # Raise an exception if the request was unsuccessful
            response.raise_for_status()
            
            # Parse the JSON response
            data = response.json()
            
            # Create the output directory if it does not exist
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Define the path to save the JSON file
            file_path = os.path.join(output_dir, f"{hash_number}.json")
            
            # Save the JSON response to a file
            with open(file_path, 'w') as json_file:
                json.dump(data, json_file, indent=4)
            
            print(f"Response saved to {file_path}")
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred for hash {hash_number}: {http_err}")
        except requests.exceptions.Timeout:
            print(f"The request timed out for hash {hash_number}")
        except requests.exceptions.RequestException as err:
            print(f"Other error occurred for hash {hash_number}: {err}")

    #open json file that was just amde, retrieve all the relevent information and embed it, delete the json file
    def getJsonDataEmbed(self,file_path):
        # Initialize empty strings for combined text and metadata
        all_texts = ""
        all_metadata = ""

        if file_path.endswith('.json'):
            with open(file_path, "r") as file:
                data = json.load(file)

            # Extract texts and metadata from the JSON data
            for item in data.get("data", []):
                sha256_hash = item.get("sha256_hash", "")
                vendor_intel = item.get("vendor_intel", {})
                vxCube = vendor_intel.get("vxCube", {})
                behaviour_list = vxCube.get("behaviour", [])
                yara_rules = item.get("yara_rules", [])
                triage = vendor_intel.get("Triage", {})

                # Extract each description in behaviour and append to textStr
                textStr = ""
                if behaviour_list is not None:

                    for behaviour in behaviour_list:
                        description = behaviour.get("rule", "")
                        #threat_level = behaviour.get("threat_level", "")
                    
                        textStr += " Behaviour description: " + description
                        #textStr += " Threat level: " + threat_level
                        textStr += "\n"  # Separate entries for better readability

                if yara_rules is not None:
                    # Append YARA rules descriptions
                    for yara_rule in yara_rules:
                        rule_name = yara_rule.get("rule_name", "")
                        author = yara_rule.get("author", "")
                        description = yara_rule.get("description", "")
                    
                        if rule_name:
                            textStr += f" YARA Rule Name: {rule_name}"
                    #if author:
                        #textStr += f" Author: {author}"
                    #if description:
                        #textStr += f" Description: {description}"
                            textStr += "\n"  # Separate entries for better readability

                
                
                signatures = triage.get("signatures", [])
                if signatures is not None:
                    
                    for signature in signatures:
                        signature_text = signature.get("signature", "")
                        #score = signature.get("score", "")
                    
                        if signature_text:
                            textStr += f" Signature: {signature_text}"
                        #if score:
                            #textStr += f" Score: {score}"
                            textStr += "\n"  # Separate entries for better readability

                # Combine metadata into a single string
                metadata_str = (
                    f"SHA256 Hash: {item.get('sha256_hash', '')}, "
                    f"SHA3-384 Hash: {item.get('sha3_384_hash', '')}, "
                    f"SHA1 Hash: {item.get('sha1_hash', '')}, "
                    f"MD5 Hash: {item.get('md5_hash', '')}, "
                    f"First Seen: {item.get('first_seen', '')}, "
                    f"Last Seen: {item.get('last_seen', '')}, "
                    f"File Name: {item.get('file_name', '')}, "
                    f"File Size: {item.get('file_size', '')}, "
                    f"File Type MIME: {item.get('file_type_mime', '')}, "
                    f"File Type: {item.get('file_type', '')}, "
                    f"Reporter: {item.get('reporter', '')}, "
                    f"Origin Country: {item.get('origin_country', '')}, "
                    #f"Anonymous: {item.get('anonymous', '')}, "
                    #f"Signature: {item.get('signature', '')}, "
                    f"IMPHASH: {item.get('imphash', '')}, "
                    f"TLSH: {item.get('tlsh', '')}, "
                    #f"TELFHASH: {item.get('telfhash', '')}, "
                    #f"GIMPHASH: {item.get('gimphash', '')}, "
                    #f"SSDEEP: {item.get('ssdeep', '')}, "
                    #f"DHash Icon: {item.get('dhash_icon', '')}, "
                    #f"Comment: {item.get('comment', '')}, "
                    #f"Archive PW: {item.get('archive_pw', '')}, "
                    f"Delivery Method: {item.get('delivery_method', '')}, "
                    f"Intelligence: {json.dumps(item.get('intelligence', {}))}, "
                    f"File Information: {json.dumps(item.get('file_information', []))}, "
                    #f"OLE Information: {json.dumps(item.get('ole_information', []))}, "
                    #f"YARA Rules: {json.dumps(item.get('yara_rules', []))}, "
                    f"Vendor Intel: {json.dumps(item.get('vendor_intel', {}))}, "
                    #f"Comments: {json.dumps(item.get('comments', []))}"
                )

                # Append to the large strings
                all_texts += textStr + "\n\n"  # Separate entries by new lines
                all_metadata += metadata_str + "\n\n"  # Separate entries by new lines

        return all_texts, all_metadata


    # Must have Function: this is the prompt that you give to the LLM, you can adjust it for your needs
    # This prompt gives the LLM the top 5 emebded chunks (releventChunks variable) and all the hashe infromation that was direcently mentioned by the user or the report (dataText and metdata variable)
    def build_messages(self, prompt: str, extra_context: str, relevantChunks, dataText: str, metadata) -> list[str, str]:
            return [
                {
                    'role': 'system',
                    'content': f'''


                                You are a cybersecurity chatbot. Analyze the following provided data about a malware hash file to answer the user's question.
                                Correct Brieif Description about the hashes******************:{dataText}.
                                Correct Hash Metadata***************: {metadata}
                                Here are some extra hash's with their relevant data:*************** {relevantChunks}
                                MORE INFORMATION POINTWISE IN DEPTH AND ALSO ANALYZE THIS AND PROVIDE WHAT TYPE OF VULNERABILITY IT MAY BE :
                                '''
                },
                {
                    # extra_context is teh file if given by the user
                    'role': 'user',
                    'content': f'{prompt} - *******************File Input (optionaly given by user)***********: {extra_context}'
                }
            ]
    

    def get_messages_with_context(self, prompt: str, extra_context: str, num_chunks: int) -> tuple[list[dict[str, str]], list[str]]:
        

        relevant_context = qd.retrieve_relevant_context(prompt,extra_context,num_chunks)
      
        allHashes = set()

        promptHashes = self.extract_sha256_hashes(prompt)
        allHashes.update(promptHashes)


        extraContextHashes = self.extract_sha256_hashes(extra_context)
        allHashes.update(extraContextHashes)

        all_dataText = ""
        all_metadtata = ""

        for hash in allHashes:
            self.fetch_json(hash, "files/mbJson")
            text, metadata = self.getJsonDataEmbed(f"files/mbJson/{hash}.json")
            #print(text)
            print("The text is:" + text)
            print("\n\n\n")
            print("The metadata is:" + metadata)

            import os

            # Path to the file you want to delete
            file_path = f'files/mbJson/{hash}.json'

    #     # Check if the file exists before trying to delete it
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"{file_path} has been deleted.")
            else:
                print(f"{file_path} does not exist.")

            all_dataText += text + "\n\n"
            all_metadtata += metadata + "\n\n"



        # pass the the retrieved data to build_message function
        messages = self.build_messages(prompt, extra_context, relevant_context, all_dataText, all_metadtata)

        return messages, relevant_context
    
    def initialize_model(self):
        # Ordered list of preferred models with their configurations
        model_options = [
            {
                "id": "meta-llama/Meta-Llama-3-8B-Instruct",
                "torch_dtype": torch.bfloat16,
                "device_map": "auto"
            },
            {
                "id": "mistralai/Mistral-7B-Instruct-v0.1",
                "torch_dtype": torch.bfloat16,
                "device_map": "auto"
            },
            {
                "id": "HuggingFaceH4/zephyr-7b-beta",
                "torch_dtype": torch.bfloat16,
                "device_map": "auto"
            },
            {
                "id": "meta-llama/Llama-2-7b-chat-hf",
                "torch_dtype": torch.float16,
                "device_map": "auto"
            }
        ]

        tokenizer = None
        model = None
        
        for model_config in model_options:
            try:
                print(f"Attempting to load model: {model_config['id']}")
                tokenizer = AutoTokenizer.from_pretrained(model_config['id'])
                model = AutoModelForCausalLM.from_pretrained(
                    model_config['id'],
                    torch_dtype=model_config['torch_dtype'],
                    device_map=model_config['device_map']
                )
                print(f"Successfully loaded model: {model_config['id']}")
                break
            except Exception as e:
                print(f"Failed to load {model_config['id']}: {str(e)}")
                continue
        
        if model is None:
            raise RuntimeError("Could not load any of the specified models")
            
        return tokenizer, model
    
    
    def prompt_llama(self,messages: list[dict],tokenizer, model):
    

        
        input_ids = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt"
        ).to(model.device)

        terminators = [
        tokenizer.eos_token_id,
        tokenizer.convert_tokens_to_ids("<|eot_id|>")
        ]

        outputs = model.generate(
        input_ids,
        max_new_tokens=500,
        eos_token_id=terminators,
        do_sample=True,
        temperature=0.6,
        top_p=0.9,
        )
        response = outputs[0][input_ids.shape[-1]:]
        print(tokenizer.decode(response, skip_special_tokens=True))


if __name__ == "__main__":

    malwareRag = Malware_Rag()
    print("Welcome to the Malware Rag App:")

    tokenizer,model=malwareRag.initialize_model()

    user_option = "2"


    while(user_option == "2"):
        user_question = input("Please enter the question you would like to ask about malware bazaar:")
        user_text_option = input("do you have any text file to input, type yes or no")
        if(user_text_option != "yes"):
            
            output, stuff = malwareRag.get_messages_with_context(user_question,"",5)
        else:
            pdfName = input("Please Enter the extract name of the pdf along with .pdf (make sure its already uploaded in the main file path)")

            text = malwareRag.extract_text_from_pdf(pdfName)

            output, stuff = malwareRag.get_messages_with_context(user_question,text,5)
        
        print(malwareRag.prompt_llama(output,tokenizer, model))

        user_option = input("Would you like to continue?")
            


