import unittest
from app import app

class TestAppBackend(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_index_route(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_student_not_found(self):
        response = self.app.get('/api/student/nonexistent')
        self.assertEqual(response.status_code, 404)

    def test_save_prep_missing_student(self):
        response = self.app.post('/api/save-prep', json={
            "student_id": "nonexistent",
            "prep_text": "Test prep"
        })
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()
