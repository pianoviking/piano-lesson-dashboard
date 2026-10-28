# Google Docs Reader

This script reads a Google Document using the Google Docs API and prints its title and content.

## Installation

1. Install required packages:
   ```bash
   pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
   ```

2. Obtain credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google Docs API
   - Create credentials for a Desktop application
   - Download the `credentials.json` file and place it in this directory

## Usage

```bash
python read_test_doc.py <document_id>
```

Replace `<document_id>` with the ID of the Google Document you want to read.

The script will authenticate using OAuth 2.0 and save the token for future use in `token.json`.