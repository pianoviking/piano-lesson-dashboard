import os
from flask import Flask, render_template, jsonify, request
from config import AppConfig
from doc_parser import parse_student_document
from googleapiclient.discovery import build
from read_test_doc import authenticate

app = Flask(__name__)
config = AppConfig()

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
        creds = authenticate()
        service = build('docs', 'v1', credentials=creds)
        document = service.documents().get(documentId=doc_id).execute()
        parsed = parse_student_document(document)
        return jsonify(parsed)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
