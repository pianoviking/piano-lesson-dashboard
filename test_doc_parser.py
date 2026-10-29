import unittest
from doc_parser import (
    extract_paragraph_text,
    get_plain_text_blocks,
    classify_semester_heading,
    parse_date_line,
    parse_field_label,
    extract_latest_lesson,
    extract_take_in_conversation,
    parse_student_document,
    parse_prep_document,
    find_student_prep,
)


class TestDocParser(unittest.TestCase):

    # -----------------------------------------------------------------------
    # Helper: Build mock Google Docs API body elements
    # -----------------------------------------------------------------------

    def _make_para_elem(self, text, style_name="NORMAL_TEXT", start_idx=0, end_idx=10):
        return {
            "startIndex": start_idx,
            "endIndex": end_idx,
            "paragraph": {
                "paragraphStyle": {"namedStyleType": style_name},
                "elements": [
                    {
                        "startIndex": start_idx,
                        "endIndex": end_idx,
                        "textRun": {"content": text},
                    }
                ],
            },
        }

    def _make_table_elem(self, cell_texts, start_idx=0, end_idx=100):
        cells = []
        for ct in cell_texts:
            cells.append({
                "content": [
                    {
                        "paragraph": {
                            "elements": [{"textRun": {"content": ct}}]
                        }
                    }
                ]
            })
        return {
            "startIndex": start_idx,
            "endIndex": end_idx,
            "table": {
                "tableRows": [
                    {"tableCells": cells}
                ]
            },
        }

    # -----------------------------------------------------------------------
    # Basic paragraph extraction & block flattening
    # -----------------------------------------------------------------------

    def test_extract_paragraph_text(self):
        para = {
            "elements": [
                {"textRun": {"content": "Hello "}},
                {"textRun": {"content": "world!\n"}},
            ]
        }
        self.assertEqual(extract_paragraph_text(para), "Hello world!\n")

    def test_get_plain_text_blocks(self):
        body_content = [
            self._make_para_elem("Intro paragraph\n"),
            self._make_table_elem(["Cell 1\n", "Cell 2\n"]),
        ]
        blocks = get_plain_text_blocks(body_content)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["type"], "paragraph")
        self.assertEqual(blocks[0]["text"], "Intro paragraph\n")
        self.assertEqual(blocks[1]["type"], "table")
        self.assertEqual(blocks[1]["text"], "Cell 1\n\nCell 2\n")

    # -----------------------------------------------------------------------
    # Semester heading classification
    # -----------------------------------------------------------------------

    def test_classify_semester_heading_dutch(self):
        self.assertEqual(classify_semester_heading("Eerste semester"), "semester_1")
        self.assertEqual(classify_semester_heading("1e semester"), "semester_1")
        self.assertEqual(classify_semester_heading("Tweede semester"), "semester_2")
        self.assertEqual(classify_semester_heading("2e semester"), "semester_2")

    def test_classify_semester_heading_english(self):
        self.assertEqual(classify_semester_heading("First semester"), "semester_1")
        self.assertEqual(classify_semester_heading("Semester 1"), "semester_1")
        self.assertEqual(classify_semester_heading("Second semester"), "semester_2")
        self.assertEqual(classify_semester_heading("Semester 2"), "semester_2")

    def test_classify_semester_heading_non_matching(self):
        self.assertIsNone(classify_semester_heading("Regular paragraph text"))
        self.assertIsNone(classify_semester_heading("Repertoire"))

    # -----------------------------------------------------------------------
    # Date & field label parsing
    # -----------------------------------------------------------------------

    def test_parse_date_line(self):
        d = parse_date_line("28/10/2026\n")
        self.assertIsNotNone(d)
        self.assertEqual(d.year, 2026)
        self.assertEqual(d.month, 10)
        self.assertEqual(d.day, 28)

        # Bolded date
        d_bold = parse_date_line("**15/09/2026**\n")
        self.assertIsNotNone(d_bold)
        self.assertEqual(d_bold.month, 9)

        # Invalid date string
        self.assertIsNone(parse_date_line("Not a date"))
        self.assertIsNone(parse_date_line("99/99/2026"))

    def test_parse_field_label(self):
        self.assertEqual(parse_field_label("**Repertoire**\n"), ("repertoire", ""))
        self.assertEqual(parse_field_label("Vaardigheden\n"), ("vaardigheden", ""))
        self.assertEqual(parse_field_label("Werkpunten"), ("werkpunten", ""))
        self.assertEqual(parse_field_label("Repertoirestuk: Mandinga"), ("repertoire", "Mandinga"))
        self.assertEqual(parse_field_label("Vaardigheid: Stijl: tumbao"), ("vaardigheden", "Stijl: tumbao"))
        self.assertEqual(parse_field_label("Werkpunten/opmerkingen: Test"), ("werkpunten", "Test"))
        self.assertEqual(parse_field_label("Werkpunten/opmerkingen:"), ("werkpunten", ""))
        self.assertEqual(parse_field_label("Random text"), (None, None))

    # -----------------------------------------------------------------------
    # Full Student Document Parsing
    # -----------------------------------------------------------------------

    def test_parse_student_document_full_workflow(self):
        doc_json = {
            "title": "Anna Kowalska - Pianoles",
            "revisionId": "rev_101",
            "body": {
                "content": [
                    self._make_para_elem("Anna's take-in conversation: started lessons in September 2025.\n"),
                    self._make_para_elem("Eerste semester\n"),
                    self._make_para_elem("15/10/2026\n"),
                    self._make_para_elem("**Repertoire**\n"),
                    self._make_para_elem("Bach Invention No. 1\nClementi Sonatina\n"),
                    self._make_para_elem("**Vaardigheden**\n"),
                    self._make_para_elem("Scales in C major\n"),
                    self._make_para_elem("**Werkpunten**\n"),
                    self._make_para_elem("Keep wrists relaxed in bar 12\n"),
                    self._make_para_elem("Tweede semester\n"),
                    self._make_para_elem("28/01/2027\n"),
                    self._make_para_elem("**Repertoire**\n"),
                    self._make_para_elem("Mozart Sonata in C\n"),
                    self._make_para_elem("**Vaardigheden**\n"),
                    self._make_para_elem("Arpeggios\n"),
                    self._make_para_elem("**Werkpunten**\n"),
                    self._make_para_elem("Dynamic contrast in B section\n"),
                ]
            },
        }

        result = parse_student_document(doc_json)

        self.assertEqual(result["title"], "Anna Kowalska - Pianoles")
        self.assertEqual(result["revision_id"], "rev_101")
        self.assertIn("take-in conversation", result["take_in_conversation"])

        # Latest lesson should pick the one in semester 2 (28/01/2027)
        lesson = result["latest_lesson"]
        self.assertIsNotNone(lesson)
        self.assertEqual(lesson["date"], "2027-01-28")
        self.assertEqual(lesson["repertoire"], "Mozart Sonata in C")
        self.assertEqual(lesson["vaardigheden"], "Arpeggios")
        self.assertEqual(lesson["werkpunten"], "Dynamic contrast in B section")
        self.assertEqual(len(result["parse_warnings"]), 0)

    # -----------------------------------------------------------------------
    # Prep Document Parsing
    # -----------------------------------------------------------------------

    def test_parse_prep_document(self):
        prep_json = {
            "title": "Lesvoorbereiding 2026-2027",
            "revisionId": "rev_202",
            "body": {
                "content": [
                    self._make_para_elem("Anna Kowalska: Check Bach invention bar 12\n"),
                    self._make_para_elem("Bob Smith - Work on posture\n"),
                    self._make_para_elem("Charlie Brown\tReview pedal technique\n"),
                ]
            },
        }

        result = parse_prep_document(prep_json)
        self.assertEqual(result["title"], "Lesvoorbereiding 2026-2027")
        self.assertEqual(len(result["entries"]), 3)

        # Test finding student prep
        anna_prep = find_student_prep(result, "Anna Kowalska")
        self.assertIsNotNone(anna_prep)
        self.assertEqual(anna_prep["prep_text"], "Check Bach invention bar 12")

        bob_prep = find_student_prep(result, "Bob Smith")
        self.assertIsNotNone(bob_prep)
        self.assertEqual(bob_prep["prep_text"], "Work on posture")

        charlie_prep = find_student_prep(result, "Charlie")
        self.assertIsNotNone(charlie_prep)
        self.assertEqual(charlie_prep["prep_text"], "Review pedal technique")

    def test_find_student_prep_ambiguous(self):
        prep_json = {
            "body": {
                "content": [
                    self._make_para_elem("Anna K: Prep 1\n"),
                    self._make_para_elem("Anna B: Prep 2\n"),
                ]
            }
        }
        result = parse_prep_document(prep_json)
        with self.assertRaises(ValueError):
            find_student_prep(result, "Anna")


if __name__ == "__main__":
    unittest.main()
