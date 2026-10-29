import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/documents']

def authenticate():
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("Error: credentials.json file is missing. Please provide the credentials file.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return creds

def fetch_document(document_id):
    try:
        creds = authenticate()
        service = build('docs', 'v1', credentials=creds)
        
        # Retrieve the document
        document = service.documents().get(documentId=document_id).execute()
        
        print('Title:', document.get('title'))
        
        # Extract text from paragraphs and table cells
        text_content = []
        body = document.get('body', {})
        content = body.get('content', [])
        
        for element in content:
            if 'paragraph' in element:
                paragraph = element['paragraph']
                elements = paragraph.get('elements', [])
                for e in elements:
                    if 'textRun' in e:
                        text_content.append(e['textRun'].get('content', ''))
            elif 'table' in element:
                table = element['table']
                for row in table.get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        cell_content = extract_text_from_cell(cell)
                        text_content.append(cell_content)
        
        # Print the full text
        full_text = ''.join(text_content)
        print(full_text)
        
    except HttpError as error:
        print(f'An error occurred: {error}')
        sys.exit(1)
    except Exception as error:
        print(f'An unexpected error occurred: {error}')
        sys.exit(1)

def extract_text_from_cell(cell):
    text_content = []
    table_cells = cell.get('content', [])
    for element in table_cells:
        if 'paragraph' in element:
            paragraph = element['paragraph']
            elements = paragraph.get('elements', [])
            for e in elements:
                if 'textRun' in e:
                    text_content.append(e['textRun'].get('content', ''))
    
    return ''.join(text_content)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python read_test_doc.py <document_id>")
        sys.exit(1)
    
    document_id = sys.argv[1]
    fetch_document(document_id)