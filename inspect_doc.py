import sys
import json
from googleapiclient.discovery import build
from config import AppConfig
from doc_parser import parse_student_document
from read_test_doc import authenticate

def inspect_document(doc_id):
    creds = authenticate()
    service = build('docs', 'v1', credentials=creds)
    
    try:
        document = service.documents().get(documentId=doc_id).execute()
        
        # Diagnostic printing
        print("--- DIAGNOSTIC: DOCUMENT BLOCKS ---")
        body = document.get('body', {})
        content = body.get('content', [])
        from doc_parser import get_plain_text_blocks
        blocks = get_plain_text_blocks(content)
        for i, b in enumerate(blocks):
            print(f"Block {i} [{b['type']}]: '{b['text'].strip()}'")
        print("-----------------------------------")
        
        result = parse_document_debug = parse_student_document(document)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error inspecting document: {e}")

if __name__ == '__main__':
    doc_id = "1qyjA_9VkrM5HkrmoVvLMHtiDdz4En-_16-w4OnHEKxU"
    inspect_document(doc_id)
