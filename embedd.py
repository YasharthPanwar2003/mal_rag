from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import VectorParams
from langchain_qdrant import QdrantVectorStore
import time
import json
import os

QDRANT_URL = 'http://localhost:6333'
COLLECTION_NAME = 'mbBazar'
VECTOR_SIZE = 1024
BATCH_SIZE = 100
EMBEDDING_DELAY_SECONDS = 5

embeddings = HuggingFaceBgeEmbeddings(
    model_name="BAAI/bge-large-en",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': False}
)

def create_collection():
    client = QdrantClient(
        url=QDRANT_URL, prefer_grpc=False
    )
        
    try:
        collections = client.get_collections()
        if any(collection.name == COLLECTION_NAME for collection in collections.collections):
            print(f'[QDRANT] Collection {COLLECTION_NAME} already exists')
        
        else:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance='Cosine'),
            )
            print(f"[QDRANT] Successfully creating collection: {COLLECTION_NAME}")

    except Exception as e:
        print(f"[ERROR] Error creating during creation collection: {COLLECTION_NAME}\n {e}")

    client.close()


def load_embeddings_custom_metadata(texts: list[str], metadata: list[dict]):
    client = QdrantClient(
        url=QDRANT_URL, prefer_grpc=False
    )
    
    text_embeddings = embeddings.embed_documents(texts)
    print(f'[QDRANT] Vector embeddings created')

    min_size = min(len(texts), len(metadata))
    for i in range(32000, min_size, BATCH_SIZE):
        batch_texts = texts[i:i + BATCH_SIZE]
        batch_metadata = metadata[i:i + BATCH_SIZE]
        batch_embeddings = text_embeddings[i:i + BATCH_SIZE]


        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=batch_metadata[n].get('id', i * BATCH_SIZE + n),
                    vector=embedding,
                    payload={
                        'metadata': batch_metadata[n],
                        'page_content': batch_texts[n]
                    }
                )
                for n, embedding in enumerate(batch_embeddings)
            ]
        )

        print(f'[QDRANT] Batch {min(i + BATCH_SIZE, min_size)} of {min_size}')
        time.sleep(EMBEDDING_DELAY_SECONDS)


    client.close()
    print("[QDRANT] Embeddings successfully loaded into collection")

def retrieve_relevant_context(query: str, file_text: str, num_matches: int) -> str:
    client = QdrantClient(
        url=QDRANT_URL, prefer_grpc=False
    )

    vector_store = QdrantVectorStore(client=client, embedding=embeddings, collection_name=COLLECTION_NAME)
    docs = vector_store.similarity_search_with_score(query=query, k=num_matches)

    # going through each relevant chunk and adding it into the string to return to the user later one
    content = []
    for i in docs:
        doc, _ = i
        content.append("-" + str(doc.metadata) + str(doc.page_content) + "\n\n")

        #if 'id' in doc.metadata:
            #content.append(doc.metadata['id'])

    client.close()

    return content


def getJsonDataEmbed2(file_path):
    # Initialize empty lists for combined text and metadata
    all_texts = []
    all_metadata = []

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
            
            part_text = ""

    
            for behaviour in behaviour_list:
                description = behaviour.get("rule", "")
                #text_parts.append(f"Behaviour description: {description}")
                part_text += f"Behaviour description: {description}"

            # Append YARA rules descriptions
            for yara_rule in yara_rules:
                rule_name = yara_rule.get("rule_name", "")
                #text_parts.append(f"YARA Rule Name: {rule_name}")
                part_text +=f"YARA Rule Name: {rule_name}"

            # Append signatures from Triage
            signatures = triage.get("signatures", [])
            for signature in signatures:
                signature_text = signature.get("signature", "")
                #text_parts.append(f"Signature: {signature_text}")
                part_text += f"Signature: {signature_text}"

            all_metadata.append({
                 'sha256_hash': item.get('sha256_hash', ''),
                    'sha3_384_hash': item.get('sha3_384_hash', ''),
                    'sha1_hash': item.get('sha1_hash', ''),
                    'md5_hash': item.get('md5_hash', ''),
                    'first_seen': item.get('first_seen', ''),
                    'last_seen': item.get('last_seen', ''),
                    'file_name': item.get('file_name', ''),
                    'file_size': item.get('file_size', ''),
                    'file_type_mime': item.get('file_type_mime', ''),
                    'file_type': item.get('file_type', ''),
                    'reporter': item.get('reporter', ''),
                    'origin_country': item.get('origin_country', ''),
                    'imphash': item.get('imphash', ''),
                    'tlsh': item.get('tlsh', ''),
                    'delivery_method': item.get('delivery_method', ''),
                    
                    
                })
            
            # Join all metadata parts for this item
            #metadata_str = "\n".join(metadata_parts)

            # Append to the lists
            all_texts.append(part_text)
    

    return all_texts, all_metadata


def read_mb_json_(folder_path: str):
    texts = []
    metadata = []

    # Ensure folder_path is a directory and iterate over each file in the folder
    if os.path.isdir(folder_path):
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)



            if file_path.endswith('.json'):
                #with open(file_path, "r") as file:
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

                # Build the text for the current item
                #text_parts = []
                part_text = ""

                # Extract each description in behaviour and append to text_parts
                if behaviour_list is not None:
                    for behaviour in behaviour_list:
                        description = behaviour.get("rule", "")
                        #text_parts.append(f"Behaviour description: {description}")
                        part_text += f"Behaviour description: {description}"

            # Append YARA rules descriptions
                if yara_rules is not None:
                    for yara_rule in yara_rules :
                        rule_name = yara_rule.get("rule_name", "")
                            #text_parts.append(f"YARA Rule Name: {rule_name}")
                        part_text +=f"YARA Rule Name: {rule_name}"

            # Append signatures from Triage
                signatures = triage.get("signatures", [])
                if signatures is not None:
                    for signature in signatures:
                        signature_text = signature.get("signature", "")
                        #text_parts.append(f"Signature: {signature_text}")
                        part_text += f"Signature: {signature_text}"

                texts.append(part_text)

            
    
                metadata.append({
                    'sha256_hash': item.get('sha256_hash', ''),
                    'sha3_384_hash': item.get('sha3_384_hash', ''),
                    'sha1_hash': item.get('sha1_hash', ''),
                    'md5_hash': item.get('md5_hash', ''),
                    'first_seen': item.get('first_seen', ''),
                    'last_seen': item.get('last_seen', ''),
                    'file_name': item.get('file_name', ''),
                    'file_size': item.get('file_size', ''),
                    'file_type_mime': item.get('file_type_mime', ''),
                    'file_type': item.get('file_type', ''),
                    'reporter': item.get('reporter', ''),
                    'origin_country': item.get('origin_country', ''),
                    'imphash': item.get('imphash', ''),
                    'tlsh': item.get('tlsh', ''),
                    'delivery_method': item.get('delivery_method', ''),
                })

    print("MARK ::")

    return texts, metadata

if __name__ == "__main__":




    create_collection()

    text, meta = read_mb_json_("output_json")


    load_embeddings_custom_metadata(text, meta)





