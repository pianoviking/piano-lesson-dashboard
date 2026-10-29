import sys
from googleapiclient.discovery import build
from config import AppConfig
from doc_parser import parse_student_document, get_plain_text_blocks
from doc_writer import build_insert_lesson_request
from read_test_doc import authenticate

def test_write_and_verify():
    creds = authenticate()
    service = build('docs', 'v1', credentials=creds)
    doc_id = "1qyjA_9VkrM5HkrmoVvLMHtiDdz4En-_16-w4OnHEKxU"
    
    # Fetch current doc
    doc = service.documents().get(documentId=doc_id).execute()
    
    # Build insert request for test date 30/10/2026
    reqs = build_insert_lesson_request(
        doc, 
        "semester_1", 
        "2026-10-30", 
        "Test Repertoire", 
        "Test Vaardigheid", 
        "Test Werkpunten"
    )
    
    print(f"Executing batchUpdate with {len(reqs)} requests...")
    service.documents().batchUpdate(documentId=doc_id, body={'requests': reqs}).execute()
    print("Successfully wrote test lesson!")
    
    # Fetch updated doc and print styles of paragraphs around the new lesson
    updated_doc = service.documents().get(documentId=doc_id).execute()
    blocks = get_plain_text_blocks(updated_doc.get('body', {}).get('content', []))
    print("--- UPDATED BLOCKS (Tail) ---")
    for i in range(max(0, len(blocks)-15), len(blocks)):
        b = blocks[i]
        if b['type'] == 'paragraph':
            # Check style of text runs
            runs = []
            for elem in b['raw_element']['paragraph'].get('elements', []):
                if 'textRun' in elem:
                    txt = elem['textRun'].get('content', '')
                    bold = elem['textRun'].get('textStyle', {}).get('bold', False)
                    runs.append(f"'{txt.strip()}' (bold={bold})")
            print(f"Block {i}: {', '.join(runs)}")

if __name__ == '__main__':
    test_write_and_verify()
