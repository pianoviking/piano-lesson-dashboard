import json
import os

DEFAULT_CONFIG_PATH = "config.json"
EXAMPLE_CONFIG_PATH = "config.json.example"

DEFAULT_CONFIG = {
    "prep_document_id": "",
    "students": [],
    "academic_calendar": {
        "semester_1": {
            "start_month": 9,
            "start_day": 1,
            "end_month": 12,
            "end_day": 24
        },
        "semester_2": {
            "start_month": 12,
            "start_day": 25,
            "end_month": 6,
            "end_day": 30
        }
    },
    "semester_headings": {
        "semester_1": ["Eerste semester", "1e semester", "First semester", "Semester 1"],
        "semester_2": ["Tweede semester", "2e semester", "Second semester", "Semester 2"]
    }
}

class AppConfig:
    def __init__(self, config_dict=None, config_path=DEFAULT_CONFIG_PATH):
        self.config_path = config_path
        self.data = config_dict if config_dict is not None else self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                return self._merge_defaults(loaded)
        elif self.config_path == DEFAULT_CONFIG_PATH and os.path.exists(EXAMPLE_CONFIG_PATH):
            with open(EXAMPLE_CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                return self._merge_defaults(loaded)
        else:
            return json.loads(json.dumps(DEFAULT_CONFIG))

    def _merge_defaults(self, loaded):
        merged = json.loads(json.dumps(DEFAULT_CONFIG))
        if isinstance(loaded, dict):
            if "prep_document_id" in loaded:
                merged["prep_document_id"] = loaded["prep_document_id"]
            if "students" in loaded and isinstance(loaded["students"], list):
                merged["students"] = loaded["students"]
            if "academic_calendar" in loaded and isinstance(loaded["academic_calendar"], dict):
                merged["academic_calendar"].update(loaded["academic_calendar"])
            if "semester_headings" in loaded and isinstance(loaded["semester_headings"], dict):
                merged["semester_headings"].update(loaded["semester_headings"])
        return merged

    def save(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    @property
    def prep_document_id(self):
        return self.data.get("prep_document_id", "")

    @prep_document_id.setter
    def prep_document_id(self, val):
        self.data["prep_document_id"] = val

    @property
    def students(self):
        return self.data.get("students", [])

    def get_student(self, student_id):
        for s in self.students:
            if s.get("id") == student_id or s.get("name") == student_id:
                return s
        return None

    def add_or_update_student(self, student_id, name, doc_id):
        for s in self.students:
            if s.get("id") == student_id:
                s["name"] = name
                s["doc_id"] = doc_id
                return s
        new_student = {"id": student_id, "name": name, "doc_id": doc_id}
        self.students.append(new_student)
        return new_student

    def remove_student(self, student_id):
        self.data["students"] = [s for s in self.students if s.get("id") != student_id]

    def determine_semester(self, date_obj):
        """
        Determines semester key ('semester_1' or 'semester_2') for a given datetime.date object.
        Returns (semester_key, warning_msg).
        September 1 to December 24 => semester_1
        December 25 to June 30 => semester_2
        July / August => outside standard academic year (warning).
        """
        month = date_obj.month
        day = date_obj.day

        # Semester 1: Sep 1 to Dec 24
        if (month == 9) or (month == 10) or (month == 11) or (month == 12 and day <= 24):
            return "semester_1", None

        # Semester 2: Dec 25 to June 30
        if (month == 12 and day >= 25) or (1 <= month <= 6):
            return "semester_2", None

        # Months 7 & 8 (July & August)
        return None, f"Date {date_obj.strftime('%Y-%m-%d')} falls in summer break (July/August) outside standard semester boundaries."
