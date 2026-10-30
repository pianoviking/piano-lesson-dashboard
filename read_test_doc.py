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
    token_path = os.environ.get("TOKEN_PATH", "token.json")
    credentials_path = os.environ.get("CREDENTIALS_PATH", "credentials.json")
    allow_browser = os.environ.get("OAUTH_ALLOW_BROWSER", "true").lower() == "true"

    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                raise RuntimeError(f"Fout bij vernieuwen van Google OAuth token: {str(e)}")
        else:
            if not os.path.exists(credentials_path):
                raise RuntimeError(f"Configuratiefout: Google OAuth credentials bestand ({credentials_path}) ontbreekt. "
                                   "Zorg ervoor dat dit bestand in de geconfigureerde map staat.")
            
            if not allow_browser:
                raise RuntimeError(f"Authenticatie vereist maar interactieve login is uitgeschakeld. "
                                   f"Zorg ervoor dat een geldig {token_path} aanwezig is in de configuratiemap.")

            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        try:
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        except Exception as e:
            # If we can't save the token (e.g. read-only mount), we still have the creds in memory
            # but next run will fail. Log it but continue if we have valid creds.
            print(f"Warning: Could not save updated token to {token_path}: {e}")
    
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