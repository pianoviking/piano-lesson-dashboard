import os
from flask import Flask, render_template, jsonify, request
from config import AppConfig
from doc_parser import parse_student_document, parse_prep_document, find_student_prep
from doc_writer import build_insert_lesson_request, build_update_prep_request
from googleapiclient.discovery import build
from read_test_doc import authenticate
from datetime import datetime
import json

app = Flask(__name__)
config = AppConfig()

def get_service():
    creds = authenticate()
    return build('docs', 'v1', credentials=creds)

@app.route('/')
def index():
    return render_template('index.html', students=config.students)

@app.route('/api/student/<student_id>')
def get_student_data(student_id):
    student = config.get_student(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    doc_id = student.get("doc_id")
    if not doc_id:
        return jsonify({"error": "No document ID configured"}), 400

    try:
        service = get_service()
        student_doc = service.documents().get(documentId=doc_id).execute()
        parsed = parse_student_document(student_doc)
        
        # Also fetch prep document to get the student's current prep
        prep_id = config.prep_document_id
        current_prep = ""
        if prep_id:
            prep_doc = service.documents().get(documentId=prep_id).execute()
            prep_data = parse_prep_document(prep_doc)
            prep_entry = find_student_prep(prep_data, student.get("name"))
            if prep_entry:
                current_prep = prep_entry.get("prep_text", "")
        
        parsed["current_prep"] = current_prep
        return jsonify(parsed)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    global config
    if request.method == 'GET':
        return jsonify({
            "prep_document_id": config.prep_document_id,
            "students": config.students
        })
    else:
        data = request.json
        prep_id = data.get('prep_document_id')
        students = data.get('students')
        
        if prep_id is not None:
            config.prep_document_id = prep_id
        if students is not None and isinstance(students, list):
            config.data['students'] = students
        
        config.save()
        return jsonify({"success": True, "prep_document_id": config.prep_document_id, "students": config.students})

@app.route('/api/save-lesson', methods=['POST'])
def save_lesson():
    data = request.json
    student_id = data.get('student_id')
    date_str = data.get('date')
    required_revision_id = data.get('revision_id') # From frontend
    
    student = config.get_student(student_id)
    if not student:
        return jsonify({"error": "Student niet gevonden"}), 404
        
    service = get_service()
    student_doc_id = student['doc_id']
    prep_doc_id = config.prep_document_id
    
    student_updated = False
    prep_updated = False
    errors = []

    # 1. Update Student Doc
    try:
        # Accept either DD/MM/YYYY (from flatpickr) or YYYY-MM-DD (from tests/API)
        try:
            lesson_date_obj = datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError:
            lesson_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            
        date_iso = lesson_date_obj.isoformat()
        
        sem, warn = config.determine_semester(lesson_date_obj)
        if not sem:
            return jsonify({"error": warn}), 400
            
        student_doc = service.documents().get(documentId=student_doc_id).execute()
        
        # Concurrency check if revision_id was provided
        if required_revision_id and student_doc.get('revisionId') != required_revision_id:
             return jsonify({
                 "error": "Document is gewijzigd door iemand anders. Ververs de pagina en probeer opnieuw.",
                 "concurrency_error": True
             }), 409

        lesson_reqs = build_insert_lesson_request(student_doc, sem, date_iso, 
                                                data['repertoire'], data['vaardigheden'], 
                                                data['werkpunten'])
        
        body = {'requests': lesson_reqs}
        if required_revision_id:
            body['writeControl'] = {'requiredRevisionId': required_revision_id}

        service.documents().batchUpdate(documentId=student_doc_id, body=body).execute()
        student_updated = True
    except ValueError as ve:
        # Pass through expected 400 errors or duplicate check errors
        if "already exists" in str(ve) or "summer break" in str(ve):
            return jsonify({"error": str(ve)}), 400
        return jsonify({"error": f"Fout bij bijwerken studentendocument: {str(ve)}"}), 500
    except Exception as e:
        err_msg = str(e)
        if "already exists" in err_msg:
            return jsonify({"error": err_msg}), 400
        return jsonify({"error": f"Fout bij bijwerken studentendocument: {err_msg}"}), 500
        
    # 2. Update Prep Doc (Optional)
    # (Removed)

    return jsonify({
        "student_updated": student_updated,
        "prep_updated": False,
        "errors": errors,
        "doc_url": f"https://docs.google.com/document/d/{student_doc_id}/edit"
    }), 200 if not errors else 207

@app.route('/api/save-prep', methods=['POST'])
def save_prep():
    data = request.json
    student_id = data.get('student_id')
    prep_text = data.get('prep_text')
    
    student = config.get_student(student_id)
    if not student:
        return jsonify({"error": "Student niet gevonden"}), 404
        
    service = get_service()
    prep_doc_id = config.prep_document_id
    
    try:
        prep_doc = service.documents().get(documentId=prep_doc_id).execute()
        prep_reqs = build_update_prep_request(prep_doc, student['name'], prep_text)
        service.documents().batchUpdate(documentId=prep_doc_id, body={'requests': prep_reqs}).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"Fout bij bijwerken voorbereidingsdocument: {str(e)}"}), 500

if __name__ == '__main__':
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "true").lower() == "true"
    app.run(host=host, port=port, debug=debug)
