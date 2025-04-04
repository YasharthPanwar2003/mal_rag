import pandas as pd
import requests
import json
import os

# Function to make the request and save the response as a JSON file
def fetch_json(hash_number, output_dir):
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

# Define the output directory where JSON files will be saved
output_dir = 'output_json'  # Replace with your desired output directory

# Load the CSV file, skipping bad lines and starting from row 2269
csv_file = 'hashFull.csv'  # Replace with your CSV file name
df = pd.read_csv(csv_file, on_bad_lines='skip', skiprows=range(1, 74020))  # Skip rows before 2269

# Assuming the column with hash numbers is named 'sha256_hash'
for hash_number in df['sha256_hash']:
    hash_number = hash_number.strip().replace('"', '')  # Remove any quotation marks and whitespace
    fetch_json(hash_number, output_dir)

print("All JSON files have been saved.")
