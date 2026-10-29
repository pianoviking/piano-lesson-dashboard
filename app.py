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

@app.route('/api/save-lesson', methods=['POST'])
def save_lesson():
    data = request.json
    student_id = data.get('student_id')
    date_str = data.get('date')
    
    student = config.get_student(student_id)
    if not student:
        return jsonify({"error": "Student niet gevonden"}), 404
        
    try:
        service = get_service()
        student_doc_id = student['doc_id']
        prep_doc_id = config.prep_document_id
        
        # 1. Update Student Doc
        sem, warn = config.determine_semester(datetime.strptime(date_str, "%Y-%m-%d").date())
        if not sem:
            return jsonify({"error": warn}), 400
            
        student_doc = service.documents().get(documentId=student_doc_id).execute()
        lesson_reqs = build_insert_lesson_request(student_doc, sem, date_str, 
                                                data['repertoire'], data['vaardigheden'], 
                                                data['werkpunten'])
        
        service.documents().batchUpdate(documentId=student_doc_id, body={'requests': lesson_reqs}).execute()
        student_updated = True
        
        # 2. Update Prep Doc (Optional)
        prep_updated = False
        if data.get('next_ideas'):
            prep_doc = service.documents().get(documentId=prep_doc_id).execute()
            prep_reqs = build_update_prep_request(prep_doc, student['name'], data['next_ideas'])
            service.documents().batchUpdate(documentId=prep_doc_id, body={'requests': prep_reqs}).execute()
            prep_updated = True
            
        return jsonify({
            "student_updated": student_updated,
            "prep_updated": prep_updated,
            "doc_url": f"https://docs.google.com/document/d/{student_doc_id}/edit"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
