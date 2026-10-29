import unittest
from unittest.mock import patch, MagicMock
from app import app
from datetime import date
from config import AppConfig

class TestPhase4Scenarios(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('app.get_service')
    def test_scenario_1_load_student(self, mock_get_service):
        """Scenario 1: Select a student and load all reference information."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        # Mock document get response
        mock_doc = {
            "title": "Test Student Doc",
            "revisionId": "rev_abc",
            "body": {
                "content": [
                    {"startIndex": 1, "endIndex": 10, "paragraph": {"elements": [{"textRun": {"content": "Take-in info\n"}}]}},
                    {"startIndex": 10, "endIndex": 20, "paragraph": {"paragraphStyle": {"namedStyleType": "HEADING_1"}, "elements": [{"textRun": {"content": "Eerste semester\n"}}]}},
                    {"startIndex": 20, "endIndex": 30, "paragraph": {"elements": [{"textRun": {"content": "15/09/2026\n"}}]}},
                    {"startIndex": 30, "endIndex": 40, "paragraph": {"elements": [{"textRun": {"content": "Repertoire\n"}}]}},
                    {"startIndex": 40, "endIndex": 50, "paragraph": {"elements": [{"textRun": {"content": "Song A\n"}}]}},
                    {"startIndex": 50, "endIndex": 60, "paragraph": {"elements": [{"textRun": {"content": "Vaardigheden\n"}}]}},
                    {"startIndex": 60, "endIndex": 70, "paragraph": {"elements": [{"textRun": {"content": "Scales\n"}}]}},
                    {"startIndex": 70, "endIndex": 80, "paragraph": {"elements": [{"textRun": {"content": "Werkpunten\n"}}]}},
                    {"startIndex": 80, "endIndex": 90, "paragraph": {"elements": [{"textRun": {"content": "Practice slow\n"}}]}},
                ]
            }
        }
        mock_service.documents().get().execute.return_value = mock_doc

        # Get first student from config
        config = AppConfig()
        if not config.students:
            config.add_or_update_student("test-s1", "Test Student", "doc_123")
            config.save()
        student_id = config.students[0]["id"]

        response = self.app.get(f'/api/student/{student_id}')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["title"], "Test Student Doc")
        self.assertIn("Take-in info", data["take_in_conversation"])
        self.assertIsNotNone(data["latest_lesson"])
        self.assertEqual(data["latest_lesson"]["date"], "2026-09-15")

    @patch('app.get_service')
    def test_scenario_6_duplicate_detection(self, mock_get_service):
        """Scenario 6: Attempt to save the same lesson twice (duplicate detection)."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        mock_doc = {
            "title": "Test Student Doc",
            "revisionId": "rev_abc",
            "body": {
                "content": [
                    {"startIndex": 1, "endIndex": 10, "paragraph": {"paragraphStyle": {"namedStyleType": "HEADING_1"}, "elements": [{"textRun": {"content": "Eerste semester\n"}}]}},
                    {"startIndex": 10, "endIndex": 20, "paragraph": {"elements": [{"textRun": {"content": "28/10/2026\n"}}]}},
                ]
            }
        }
        mock_service.documents().get().execute.return_value = mock_doc

        config = AppConfig()
        student_id = config.students[0]["id"] if config.students else "test-s1"

        response = self.app.post('/api/save-lesson', json={
            "student_id": student_id,
            "date": "2026-10-28",
            "repertoire": "Rep",
            "vaardigheden": "Vard",
            "werkpunten": "Werk"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("already exists", response.get_json()["error"])

    @patch('app.get_service')
    def test_scenario_8_out_of_range_date(self, mock_get_service):
        """Scenario 8: Handle an ambiguous or out-of-range date (summer break)."""
        config = AppConfig()
        student_id = config.students[0]["id"] if config.students else "test-s1"

        response = self.app.post('/api/save-lesson', json={
            "student_id": student_id,
            "date": "2026-07-15", # July falls in summer break
            "repertoire": "Rep",
            "vaardigheden": "Vard",
            "werkpunten": "Werk"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("summer break", response.get_json()["error"])

    @patch('app.get_service')
    def test_scenario_11_concurrent_edit_conflict(self, mock_get_service):
        """Scenario 11: Handle a document modified by a student while the application is open (concurrency conflict)."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        mock_doc = {
            "title": "Test Student Doc",
            "revisionId": "rev_NEW_123", # Different from requested revision_id
            "body": {"content": []}
        }
        mock_service.documents().get().execute.return_value = mock_doc

        config = AppConfig()
        student_id = config.students[0]["id"] if config.students else "test-s1"

        response = self.app.post('/api/save-lesson', json={
            "student_id": student_id,
            "date": "2026-10-28",
            "repertoire": "Rep",
            "vaardigheden": "Vard",
            "werkpunten": "Werk",
            "revision_id": "rev_OLD_999" # Mismatched revision ID
        })
        self.assertEqual(response.status_code, 409)
        data = response.get_json()
        self.assertTrue(data.get("concurrency_error"))

if __name__ == '__main__':
    unittest.main()
