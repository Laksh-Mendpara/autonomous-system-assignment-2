"""
Academic Helpdesk Agent Tools
IIT Jodhpur Academic System
"""

import os
import csv
import json
import re
from datetime import datetime

DATA_DIR = "/home/laksh/autonomous_assignment/data"
TIMETABLE_SEM1 = os.path.join(DATA_DIR, "timetable/timetable_sem1_all_courses.csv")
TIMETABLE_SEM2 = os.path.join(DATA_DIR, "timetable/timetable_sem2_all_courses.csv")
FACULTY_DIR = os.path.join(DATA_DIR, "faculty/faculty_email_directory.csv")
COURSE_MAP = os.path.join(DATA_DIR, "faculty/course_instructor_map.csv")
UNANSWERED_LOG = "/home/laksh/autonomous_assignment/unanswered_questions.jsonl"

SLOT_TIMINGS = {
    "A": "Monday, Wednesday, Friday 08:00 - 08:55 AM",
    "B": "Monday, Wednesday, Friday 09:00 - 09:55 AM",
    "C": "Monday, Wednesday, Friday 10:00 - 10:55 AM",
    "D": "Tuesday, Thursday, Saturday 08:00 - 08:55 AM",
    "E": "Tuesday, Thursday, Saturday 09:00 - 09:55 AM",
    "F": "Tuesday, Thursday, Saturday 10:00 - 10:55 AM",
    "G": "Monday, Wednesday, Friday 11:00 - 11:55 AM",
    "H": "Tuesday, Thursday, Saturday 11:00 - 11:55 AM",
    "I": "Monday, Wednesday, Friday 02:00 - 02:55 PM",
    "J": "Tuesday, Thursday, Saturday 02:00 - 02:55 PM",
    "K": "Monday, Wednesday, Friday 03:00 - 03:55 PM",
    "L": "Tuesday, Thursday, Saturday 03:00 - 03:55 PM",
    "M": "Monday, Wednesday, Friday 04:00 - 04:55 PM",
    "N": "Tuesday, Thursday, Saturday 04:00 - 04:55 PM",
}

def lookup_course_slot(course_identifier: str, semester: str = None) -> list:
    """
    Search timetable for course slot and timings by course code or course name.
    """
    query = course_identifier.strip().lower()
    results = []
    
    files = []
    if semester == "Sem1" or semester == "1":
        files = [(TIMETABLE_SEM1, "Sem1")]
    elif semester == "Sem2" or semester == "2":
        files = [(TIMETABLE_SEM2, "Sem2")]
    else:
        files = [(TIMETABLE_SEM1, "Sem1"), (TIMETABLE_SEM2, "Sem2")]
        
    for filepath, sem in files:
        if not os.path.exists(filepath):
            continue
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get('course_code', '').strip().lower()
                name = row.get('course_name', '').strip().lower()
                if query in code or query in name or code in query:
                    slot_letter = row.get('slot', '').split()[0].upper()
                    timing = SLOT_TIMINGS.get(slot_letter, "Special Slot / Lab timing as per department notice")
                    results.append({
                        "course_code": row.get('course_code'),
                        "course_name": row.get('course_name'),
                        "instructor": row.get('instructor'),
                        "slot": row.get('slot'),
                        "timing": timing,
                        "ltp": row.get('ltp'),
                        "credits": row.get('credits'),
                        "dept": row.get('dept'),
                        "semester": sem,
                        "citation": f"Timetable {sem} ({row.get('dept')} Department)"
                    })
    return results

def get_instructor_email(query: str) -> list:
    """
    Find faculty email by course code, course name, or instructor name.
    """
    q = query.strip().lower()
    results = []
    
    # Check course map first
    if os.path.exists(COURSE_MAP):
        with open(COURSE_MAP, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get('course_code', '').strip().lower()
                name = row.get('course_name', '').strip().lower()
                inst = row.get('instructor', '').strip().lower()
                if q in code or q in name or q in inst:
                    results.append({
                        "course_code": row.get('course_code'),
                        "course_name": row.get('course_name'),
                        "instructor": row.get('instructor'),
                        "email": row.get('email'),
                        "dept": row.get('dept'),
                        "semester": row.get('semester'),
                        "citation": "Course-Instructor Directory (data/faculty/course_instructor_map.csv)"
                    })
                    
    # Also check faculty directory
    if not results and os.path.exists(FACULTY_DIR):
        with open(FACULTY_DIR, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('instructor_name', '').strip().lower()
                if q in name:
                    results.append({
                        "instructor": row.get('instructor_name'),
                        "email": row.get('email'),
                        "dept": row.get('dept'),
                        "citation": "Faculty Email Directory (data/faculty/faculty_email_directory.csv)"
                    })
    return results

def count_floated_courses(dept: str = "HS", level: str = "400", semester: str = "Sem1") -> dict:
    """
    Count how many courses of a specific level have been floated by a department in a semester.
    E.g. dept="Humanities" or "HS", level="400", semester="Sem1"
    """
    filepath = TIMETABLE_SEM1 if semester.lower() in ["sem1", "1"] else TIMETABLE_SEM2
    sem_label = "Semester 1" if semester.lower() in ["sem1", "1"] else "Semester 2"
    
    dept_aliases = {
        "humanities": ["hs", "sola", "lal", "lap"],
        "hs": ["hs", "sola", "lal", "lap"],
        "cse": ["cse", "cs", "csl", "csp", "csn"],
        "ee": ["ee", "eel", "eep"],
        "me": ["me", "mel", "mep"],
        "math": ["ma", "math", "mal", "map"]
    }
    
    target_prefixes = dept_aliases.get(dept.lower(), [dept.lower()])
    
    matched_courses = []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_dept = row.get('dept', '').strip().lower()
                code = row.get('course_code', '').strip()
                # Check department match
                dept_match = row_dept in target_prefixes or any(code.lower().startswith(p) for p in target_prefixes)
                if not dept_match:
                    continue
                # Check level match (e.g. 400 level -> 4xxx)
                if level:
                    # Match digits like 4xxx
                    num_match = re.search(r'(\d+)', code)
                    if num_match:
                        code_num = num_match.group(1)
                        if level.startswith("4") and code_num.startswith("4"):
                            matched_courses.append(row)
                        elif level.startswith("7") and code_num.startswith("7"):
                            matched_courses.append(row)
                        elif code_num.startswith(level[0]):
                            matched_courses.append(row)
                else:
                    matched_courses.append(row)
                    
    return {
        "department": dept,
        "level": f"{level}-level",
        "semester": sem_label,
        "count": len(matched_courses),
        "courses": [{
            "code": r.get('course_code'),
            "name": r.get('course_name'),
            "instructor": r.get('instructor'),
            "slot": r.get('slot'),
            "credits": r.get('credits')
        } for r in matched_courses],
        "citation": f"Timetable {sem_label} ({dept} Department / SoLA)"
    }

def draft_leave_email(course_code: str, reason: str = "sick-leave", duration_days: int = 2,
                      student_name: str = "[Student Name]", student_roll: str = "[Roll Number]",
                      start_date: str = "[Start Date]", end_date: str = "[End Date]") -> dict:
    """
    Draft an email to a course instructor for leave or makeup exam permission.
    """
    # Lookup instructor
    info = get_instructor_email(course_code)
    if info:
        instructor_name = info[0].get('instructor', 'Professor')
        instructor_email = info[0].get('email', 'instructor@iitj.ac.in')
        course_name = info[0].get('course_name', course_code)
    else:
        instructor_name = "Course Instructor"
        instructor_email = "instructor@iitj.ac.in"
        course_name = course_code
        
    subject = f"Application for Sick Leave — {course_code} ({course_name}) — {student_name} ({student_roll})"
    
    body = f"""To: {instructor_name} <{instructor_email}>
Subject: {subject}

Respected Dr. {instructor_name.split()[-1] if instructor_name else 'Instructor'},

I am writing to formally request leave of absence from classes for the course {course_code}: {course_name} for a period of {duration_days} day(s) (from {start_date} to {end_date}) due to {reason}.

As per the Institute Academic Regulations (Section 15/23 on Leave Rules and Circular No. IITJ/OAA/Circular/2024-25/51682), I have consulted the Institute Medical Officer (IMO) and am attaching the required medical prescription / fitness certificate for your reference.

I will ensure that I catch up on all lecture notes, tutorial problems, and lab exercises covered during my absence. In case any quiz, assignment, or continuous evaluation component is held during this period, I request your kind permission to submit the missed work or appear for a make-up evaluation as per Section 8 of the Academic Regulations.

Thank you very much for your understanding and consideration.

Sincerely,
{student_name}
Roll No: {student_roll}
Department of Computer Science and Engineering
Indian Institute of Technology Jodhpur
"""
    return {
        "recipient_name": instructor_name,
        "recipient_email": instructor_email,
        "subject": subject,
        "body": body,
        "citation": "Leave Rules (Academic Regulations Section 15 & 23, Circular 51682)"
    }

def log_unanswered_question(question: str, reason: str = "out_of_scope", metadata: dict = None) -> bool:
    """
    Log an unanswered or out-of-scope question to the human review log.
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "reason": reason,
        "metadata": metadata or {}
    }
    with open(UNANSWERED_LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + "\n")
    return True
