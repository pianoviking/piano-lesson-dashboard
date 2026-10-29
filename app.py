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
        document = service.documents().get(documentId=doc_id).execute()
        parsed = parse_student_document(document)
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
        sem, warn = config.determine_semester(datetime.strptime(date_str, "%Y-%m-%d").date())
        if not sem:
            return jsonify({"error": warn}), 400
            
        student_doc = service.documents().get(documentId=student_doc_id).execute()
        
        # Concurrency check if revision_id was provided
        if required_revision_id and student_doc.get('revisionId') != required_revision_id:
             return jsonify({
                 "error": "Document is gewijzigd door iemand anders. Ververs de pagina en probeer opnieuw.",
                 "concurrency_error": True
             }), 409

        lesson_reqs = build_insert_lesson_request(student_doc, sem, date_str, 
                                                data['repertoire'], data['vaardigheden'], 
                                                data['werkpunten'])
        
        body = {'requests': lesson_reqs}
        if required_revision_id:
            body['writeControl'] = {'requiredRevisionId': required_revision_id}

        service.documents().batchUpdate(documentId=student_doc_id, body=body).execute()
        student_updated = True
    except Exception as e:
        return jsonify({"error": f"Fout bij bijwerken studentendocument: {str(e)}"}), 500
        
    # 2. Update Prep Doc (Optional)
    if data.get('next_ideas'):
        try:
            prep_doc = service.documents().get(documentId=prep_doc_id).execute()
            prep_reqs = build_update_prep_request(prep_doc, student['name'], data['next_ideas'])
            service.documents().batchUpdate(documentId=prep_doc_id, body={'requests': prep_reqs}).execute()
            prep_updated = True
        except Exception as e:
            errors.append(f"Fout bij bijwerken voorbereidingsdocument: {str(e)}")
            
    return jsonify({
        "student_updated": student_updated,
        "prep_updated": prep_updated,
        "errors": errors,
        "doc_url": f"https://docs.google.com/document/d/{student_doc_id}/edit"
    }), 200 if not errors else 207

if __name__ == '__main__':
    app.run(port=5000, debug=True)
