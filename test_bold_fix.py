import sys
from googleapiclient.discovery import build
from doc_parser import get_plain_text_blocks
from doc_writer import build_insert_lesson_request, format_lesson_entry_data, check_duplicate_lesson, find_semester_insertion_index
from read_test_doc import authenticate

def build_insert_lesson_request_fixed(document_json, semester_key, lesson_date_str, repertoire, vaardigheden, werkpunten):
    if check_duplicate_lesson(document_json, lesson_date_str):
        raise ValueError(f"A lesson entry for date {lesson_date_str} already exists for this student document.")

    body = document_json.get("body", {})
    content = body.get("content", [])
    blocks = get_plain_text_blocks(content)

    insert_idx = find_semester_insertion_index(blocks, semester_key)
    data = format_lesson_entry_data(lesson_date_str, repertoire, vaardigheden, werkpunten)
    
    line_date = f"{data['date']}\n"
    line_rep = f"{data['repertoire_label']}{data['repertoire_val']}\n"
    line_vaa = f"{data['vaardigheid_label']}{data['vaardigheid_val']}\n"
    line_wer = f"{data['werkpunten_label']}{data['werkpunten_val']}\n"
    trailing_sep = "\n"

    full_text = line_date + line_rep + line_vaa + line_wer + trailing_sep

    requests = [
        {
            "insertText": {
                "location": {
                    "index": insert_idx
                },
                "text": full_text
            }
        },
        # FIRST: Explicitly un-bold the entire inserted range so it doesn't inherit bold from surrounding text
        {
            "updateTextStyle": {
                "range": {
                    "startIndex": insert_idx,
                    "endIndex": insert_idx + len(full_text)
                },
                "textStyle": {"bold": False},
                "fields": "bold"
            }
        }
    ]

    # SECOND: Explicitly bold ONLY the date and labels
    curr = insert_idx

    # Bold date
    requests.append({
        "updateTextStyle": {
            "range": {
                "startIndex": curr,
                "endIndex": curr + len(data['date'])
            },
            "textStyle": {"bold": True},
            "fields": "bold"
        }
    })
    curr += len(line_date)

    # Bold "Repertoirestuk: "
    requests.append({
        "updateTextStyle": {
            "range": {
                "startIndex": curr,
                "endIndex": curr + len(data['repertoire_label'])
            },
            "textStyle": {"bold": True},
            "fields": "bold"
        }
    })
    curr += len(line_rep)

    # Bold "Vaardigheid: "
    requests.append({
        "updateTextStyle": {
            "range": {
                "startIndex": curr,
                "endIndex": curr + len(data['vaardigheid_label'])
            },
            "textStyle": {"bold": True},
            "fields": "bold"
        }
    })
    curr += len(line_vaa)

    # Bold "Werkpunten/opmerkingen: "
    requests.append({
        "updateTextStyle": {
            "range": {
                "startIndex": curr,
                "endIndex": curr + len(data['werkpunten_label'])
            },
            "textStyle": {"bold": True},
            "fields": "bold"
        }
    })

    return requests

def test_fixed_bolding():
    creds = authenticate()
    service = build('docs', 'v1', credentials=creds)
    doc_id = "1qyjA_9VkrM5HkrmoVvLMHtiDdz4En-_16-w4OnHEKxU"
    
    doc = service.documents().get(documentId=doc_id).execute()
    
    reqs = build_insert_lesson_request_fixed(
        doc, 
        "semester_1", 
        "2026-10-31", 
        "Unbolded Repertoire Test", 
        "Unbolded Vaardigheid Test", 
        "Unbolded Werkpunten Test"
    )
    
    service.documents().batchUpdate(documentId=doc_id, body={'requests': reqs}).execute()
    print("Write completed successfully!")

    # Verify formatting in response
    updated_doc = service.documents().get(documentId=doc_id).execute()
    content = updated_doc.get('body', {}).get('content', [])
    for element in content:
        if 'paragraph' in element:
            for elem in element['paragraph'].get('elements', []):
                if 'textRun' in elem:
                    txt = elem['textRun'].get('content', '').strip()
                    bold = elem['textRun'].get('textStyle', {}).get('bold', False)
                    if '31/10' in txt or 'Unbolded' in txt:
                        print(f"Run: '{txt}' -> bold={bold}")

if __name__ == '__main__':
    test_fixed_bolding()
