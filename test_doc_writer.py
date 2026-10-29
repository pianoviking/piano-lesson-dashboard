import unittest
from doc_writer import format_lesson_entry_data, check_duplicate_lesson, find_semester_insertion_index, build_insert_lesson_request
from doc_parser import get_plain_text_blocks

class TestDocWriter(unittest.TestCase):
    def test_format_lesson_entry_data(self):
        data = format_lesson_entry_data("2026-10-28", "Bach Invention", "Scales", "Relax wrists")
        self.assertEqual(data["date"], "28/10")
        self.assertEqual(data["repertoire_label"], "Repertoirestuk: ")
        self.assertEqual(data["repertoire_val"], "Bach Invention")

    def test_check_duplicate_lesson(self):
        doc_json = {
            "body": {
                "content": [
                    {"startIndex": 1, "endIndex": 10, "paragraph": {"elements": [{"textRun": {"content": "28/10/2026\n"}}]}}
                ]
            }
        }
        self.assertTrue(check_duplicate_lesson(doc_json, "2026-10-28"))
        self.assertFalse(check_duplicate_lesson(doc_json, "2026-10-29"))

    def test_find_semester_insertion_index(self):
        doc_json = {
            "body": {
                "content": [
                    {"startIndex": 1, "endIndex": 10, "paragraph": {"elements": [{"textRun": {"content": "Semester 1\n"}}]}},
                    {"startIndex": 10, "endIndex": 20, "paragraph": {"elements": [{"textRun": {"content": "15/09/2026\n"}}]}},
                    {"startIndex": 20, "endIndex": 30, "paragraph": {"elements": [{"textRun": {"content": "Semester 2\n"}}]}},
                ]
            }
        }
        blocks = get_plain_text_blocks(doc_json["body"]["content"])
        idx = find_semester_insertion_index(blocks, "semester_1")
        self.assertEqual(idx, 19) # Right before Semester 2 start index (20 - 1)

if __name__ == "__main__":
    unittest.main()
