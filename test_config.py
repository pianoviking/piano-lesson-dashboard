import unittest
import os
import json
import datetime
import tempfile
from config import AppConfig

class TestAppConfig(unittest.TestCase):
    def test_default_config_structure(self):
        config = AppConfig(config_dict={})
        self.assertEqual(config.prep_document_id, "")
        self.assertEqual(config.students, [])

    def test_student_management(self):
        config = AppConfig(config_dict={"students": []})
        config.add_or_update_student("s1", "Alice", "doc123")
        self.assertEqual(len(config.students), 1)
        self.assertEqual(config.get_student("s1")["name"], "Alice")
        
        # Update student
        config.add_or_update_student("s1", "Alice Smith", "doc123_updated")
        self.assertEqual(len(config.students), 1)
        self.assertEqual(config.get_student("s1")["name"], "Alice Smith")
        self.assertEqual(config.get_student("s1")["doc_id"], "doc123_updated")

        # Remove student
        config.remove_student("s1")
        self.assertEqual(len(config.students), 0)

    def test_determine_semester(self):
        config = AppConfig()

        # Semester 1 tests: Sep 1 - Dec 24
        sem, warn = config.determine_semester(datetime.date(2026, 9, 1))
        self.assertEqual(sem, "semester_1")
        self.assertIsNone(warn)

        sem, warn = config.determine_semester(datetime.date(2026, 12, 24))
        self.assertEqual(sem, "semester_1")
        self.assertIsNone(warn)

        # Semester 2 tests: Dec 25 - Jun 30
        sem, warn = config.determine_semester(datetime.date(2026, 12, 25))
        self.assertEqual(sem, "semester_2")
        self.assertIsNone(warn)

        sem, warn = config.determine_semester(datetime.date(2027, 1, 15))
        self.assertEqual(sem, "semester_2")
        self.assertIsNone(warn)

        sem, warn = config.determine_semester(datetime.date(2027, 6, 30))
        self.assertEqual(sem, "semester_2")
        self.assertIsNone(warn)

        # Summer break tests: July & August
        sem, warn = config.determine_semester(datetime.date(2026, 7, 15))
        self.assertIsNone(sem)
        self.assertIsNotNone(warn)

    def test_save_and_load_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, "config.json")
            config = AppConfig(config_path=cfg_path)
            config.prep_document_id = "prep_doc_999"
            config.add_or_update_student("s2", "Bob", "doc_bob")
            config.save()

            self.assertTrue(os.path.exists(cfg_path))

            # Load back
            loaded_config = AppConfig(config_path=cfg_path)
            self.assertEqual(loaded_config.prep_document_id, "prep_doc_999")
            self.assertEqual(len(loaded_config.students), 1)
            self.assertEqual(loaded_config.students[0]["name"], "Bob")

if __name__ == "__main__":
    unittest.main()
