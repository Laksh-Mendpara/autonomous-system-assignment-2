# Academic Helpdesk System — 25 Benchmark Evaluation Questions

This document presents the complete 25-question evaluation benchmark used to assess the Multi-Agent Academic Helpdesk System for IIT Jodhpur.

---

## 1. Academic Policy & Regulation Queries

| ID | Prompt Question | Expected Specialist | Ground Truth & Factual Target | Expected Citations |
|---|---|---|---|---|
| **POL_01** | *What is the attendance requirement to sit in the Major exam?* | `PolicyAgent` | Minimum 75% attendance in lectures, tutorials, and practicals. Medical condonation considered for 65%–75% with IMO validation. Strictly below 65% results in a DX (Debarred) grade. | `circular_attendance_amendment_2024.md`, `Academic Regulations Sec 4.1.9` |
| **POL_02** | *What happens if my attendance in a course falls below 65%?* | `PolicyAgent` | Student is awarded a DX (Debarred) grade and disqualified from writing the Major exam. | `circular_attendance_amendment_2024.md`, `attendance_policy_detail.md` |
| **POL_03** | *How many Open Elective credits do I need to earn in order to get a B.Tech. Degree?* | `PolicyAgent` | Regular B.Tech. students must earn 10 to 12 Open Elective (OE) credits outside their parent discipline. | `btech_credit_requirements.md`, `IITJ CSE Curriculum Guide`, `Academic Regulations Sec 11.3` |
| **POL_04** | *What are the rules for make-up examinations if I miss Minor 1 due to illness?* | `PolicyAgent` | Apply within 3 working days with IMO-endorsed medical certificate. Minor makeup requires Course Instructor approval. Major makeup requires Dean approval. | `makeup_exam_policy.md`, `circular_exam_policy_amendment_2024.md`, `Academic Regulations Sec 8` |
| **POL_05** | *What is the minimum CGPA required for branch change at the end of first year for general category?* | `PolicyAgent` | Minimum CGPA of 8.5 at the end of Semester II with zero backlogs and no disciplinary issues. | `branch_change_policy.md`, `Academic Regulations Sec 16` |
| **POL_06** | *Can I withdraw from a course after the add-drop deadline, and what grade is awarded?* | `PolicyAgent` | Withdrawal permitted within first 4 weeks; awarded a 'W' grade that does not impact GPA. | `course_registration_rules.md`, `Academic Regulations Sec 3.4` |

---

## 2. Schedule, Slot & Timetable Queries

| ID | Prompt Question | Expected Specialist | Ground Truth & Factual Target | Expected Citations |
|---|---|---|---|---|
| **SCH_01** | *What is the slot for the course Autonomous Systems?* | `ScheduleAgent` | **Slot H** (Tuesday, Thursday, Saturday 11:00 AM – 11:55 AM), taught by Dr. Ashok Joshi. | `timetable_sem1_all_courses.csv (RM Dept)`, `slot_timing_guide.md` |
| **SCH_02** | *What are the class timings and days for Slot H?* | `ScheduleAgent` | Tuesday, Thursday, and Saturday 11:00 AM – 11:55 AM. | `slot_timing_guide.md` |
| **SCH_03** | *How many 400 level electives have been floated by the Humanities department in this semester?* | `ScheduleAgent` | Exactly **11 electives** in Semester 1 (LAL4060, LAL4650, LAL4040, LAL4360, LAL4030, LAL4380, LAL4110, LAL4680, LAL4350, LAL4400, LAL4720). | `timetable_sem1_all_courses.csv (SoLA Dept)`, `humanities_courses_sem1.md` |
| **SCH_04** | *How many 400 level electives are offered by Humanities department in Semester 2?* | `ScheduleAgent` | Exactly **10 electives** in Semester 2 (LAL4110, LAL4680, LAL4030, LAL4050, LAL4040, LAL4370, LAL4380, LAL4350, LAL4650, LAP4120). | `timetable_sem2_all_courses.csv (SoLA Dept)`, `humanities_courses_sem2.md` |
| **SCH_05** | *What is the slot and instructor for CSL2020 Data Structure and Algorithm in Sem 1?* | `ScheduleAgent` | Slot B (Mon/Wed/Fri 09:00–09:55 AM), taught by Dr. Suchetana Chakraborty (LTP: 3-0-2, 4.0 credits). | `timetable_sem1_all_courses.csv (CSE Dept)` |
| **SCH_06** | *What is the timing of Slot A lectures?* | `ScheduleAgent` | Monday, Wednesday, and Friday from 08:00 AM to 08:55 AM. | `slot_timing_guide.md` |

---

## 3. Faculty Communication & Leave Email Drafting

| ID | Prompt Question | Expected Specialist | Ground Truth & Factual Target | Expected Citations |
|---|---|---|---|---|
| **EML_01** | *Write an email to the course instructor of CSL7570 that I need leave for 2 days* | `EmailAgent` | Dr. Ashok Joshi (`ashok.joshi@iitj.ac.in`). Formats structured email draft citing IMO consultation and make-up provisions. | `Leave Rules (Sec 15 & 23, Circular 51682)`, `course_instructor_map.csv` |
| **EML_02** | *Draft an email to instructor of Autonomous Systems requesting sick leave for 3 days due to fever* | `EmailAgent` | Dr. Ashok Joshi (`ashok.joshi@iitj.ac.in`). Formats sick-leave draft for 3 days with medical attachment note. | `Leave Rules (Sec 15 & 23)`, `course_instructor_map.csv` |
| **EML_03** | *Write an email to course instructor of CSL3080 Computer Networks seeking permission for make-up quiz* | `EmailAgent` | Dr. Nitin Awathare (`nitin.awathare@iitj.ac.in`). Formats make-up quiz petition citing Academic Regulations Section 8. | `Academic Regulations Sec 8`, `course_instructor_map.csv` |
| **EML_04** | *Draft an email to instructor of CSL4020 Deep Learning for 2 days medical leave* | `EmailAgent` | Dr. Angshuman Paul (`angshuman.paul@iitj.ac.in`) / Dr. Pratik Mazumder. Formats 2-day medical leave application. | `Leave Rules`, `course_instructor_map.csv` |
| **EML_05** | *What is the official email address of Dr. Ashok Joshi in CSE department?* | `EmailAgent` | `ashok.joshi@iitj.ac.in` (CSE / IDRP Department). | `faculty_email_directory.csv` |
| **EML_06** | *Write an email to the instructor of CSL2060 Software Engineering applying for 1 day leave* | `EmailAgent` | Dr. Romi Banerjee (`romi.banerjee@iitj.ac.in`). Formats 1-day absence request. | `Leave Rules`, `course_instructor_map.csv` |

---

## 4. Strict Out-of-Scope Guard (Refusal & Logging)

| ID | Prompt Question | Expected Action | Handled By | System Behavior |
|---|---|---|---|---|
| **OOS_01** | *What are the available dining options on the campus?* | Explicit Refusal | `Orchestrator Guard` | States lack of non-academic dining information; logs to `unanswered_questions.jsonl`. |
| **OOS_02** | *What is the best way to reach the campus from Jodhpur city center?* | Explicit Refusal | `Orchestrator Guard` | States city transit/travel is outside academic helpdesk scope; logs to `unanswered_questions.jsonl`. |
| **OOS_03** | *Where can I find late-night snacks or canteens inside the campus?* | Explicit Refusal | `Orchestrator Guard` | Refuses non-academic eatery query; logs to audit trail. |
| **OOS_04** | *How do I book a cab from Jodhpur railway station to IIT Jodhpur?* | Explicit Refusal | `Orchestrator Guard` | Refuses railway transit inquiry; logs to audit trail. |
| **OOS_05** | *What sports tournaments are scheduled in the campus gym this weekend?* | Explicit Refusal | `Orchestrator Guard` | Refuses extracurricular gym inquiry; logs to audit trail. |
| **OOS_06** | *What is the weather forecast for Jodhpur this week?* | Explicit Refusal | `Orchestrator Guard` | Refuses weather inquiry; logs to audit trail. |
| **OOS_07** | *Which hostel has the best laundry facilities on campus?* | Explicit Refusal | `Orchestrator Guard` | Refuses hostel amenities inquiry; logs to audit trail. |

