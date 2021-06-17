from __future__ import print_function
import http.client
import json
import datetime
import gc
import time
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import sys
import threading

SCOPES = ['https://www.googleapis.com/auth/classroom.courses.readonly','https://www.googleapis.com/auth/classroom.profile.emails', 'https://www.googleapis.com/auth/classroom.rosters.readonly', 'https://www.googleapis.com/auth/classroom.coursework.students']

student_dict = {}
classes_dict = {}
students_in_class_dict = {}
student_id_refrence = {}

def initialize():
    """Shows basic usage of the Classroom API.
    Prints the names of the first 10 courses the user has access to.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    global service
    service = build('classroom', 'v1', credentials=creds)
    
    #teachers = service.courses().teachers().list(courseId='122494904009').execute()
    #for teacher in teachers['teachers']:
        #print(teacher['profile']['emailAddress'], teacher['profile']['name']['fullName'])

def get_courses():
    global service
    courses = service.courses().list().execute()
    return courses['courses']

def coursework_thread(course):
    coursework = service.courses().courseWork().list(courseId=course["id"]).execute()
    try:
        classes_dict[course["id"]] = coursework["courseWork"]
    except: pass

def students_thread(course):
    students = service.courses().students().list(courseId=course["id"]).execute()
    student_id_refrence[course["id"]] = [student["userId"] for student in students["students"]]

def get_coursework(course_list):
    #threads1 = []
    #threads2 = []
    for course in course_list:
    #    t1 = threading.Thread(target=coursework_thread, args=[course])
    #    t2 = threading.Thread(target=students_thread, args=[course])
    #    t1.daemon = True
    #    t2.daemon = True
    #    threads1.append(t1)
    #    threads2.append(t2)
    #for i in range(len(course_list)):
    #    threads1[i].start()
    #    time.sleep(1)
    #    threads2[i].start()
    #    time.sleep(1)
    #for i in range(len(course_list)):
    #    threads1[i].join()
    #    threads2[i].join()
        coursework = service.courses().courseWork().list(courseId=course["id"]).execute()
        try:
            classes_dict[course["id"]] = coursework["courseWork"]
        except: pass
        #----------------------------------------------------------------------------------------------
        students = service.courses().students().list(courseId=course["id"]).execute()
        student_id_refrence[course["id"]] = [student["userId"] for student in students["students"]]
        #for student in students["students"]:
            #student_id = student["userId"]
            #if not (student_id in student_dict):
            #    student_dict[student_id] = []
            #try:
            #    student_dict[student_id].extend(coursework["courseWork"])
            #except: pass
    with open('classes_dict.json', 'w') as file:
        json.dump(classes_dict, file)
    #with open('student_dict.json', 'w') as file:
    #    json.dump(student_dict, file)
    with open('student_ids.json', 'w') as file:
        json.dump(student_id_refrence, file)

def get_old_coursework_data():
    global classes_dict
    #global student_dict
    global student_id_refrence
    with open('classes_dict.json') as file:
        classes_dict = json.load(file)
        print('done')
    #with open('student_dict.json') as file:
    #    student_dict = json.load(file)
    #    print('done')
    with open('student_ids.json') as file:
        student_id_refrence = json.load(file)
        print('done')
    #with open('per_course_schedule.json') as file:
        #students_in_class_dict = json.load(file)
        #print('done')

def get_all_course_schedule(course_list):
    for course in course_list:
        students_in_class_dict[course["id"]] = []
        for student_id in student_id_refrence[course["id"]]:
            students_in_class_dict[course["id"]].extend(student_dict[student_id])
    with open('per_course_schedule.json', 'w') as file:
        json.dump(students_in_class_dict, file)

def get_single_course_schedule(course_list, course_id, duplicates=True, include_given_course=True, min_date={'year': 0, 'month': 0, 'day': 0}, max_date={'year': 9999, 'month': 9999, 'day': 9999}):
    used_ids = []
    for course in course_list:
        if course_id == course["id"]: break
    student_work = []
    for student_id in student_id_refrence[course["id"]]:
        for id in [course_id for course_id in student_id_refrence if (student_id in student_id_refrence[course_id])]:
            try:
                if (id not in used_ids) and (include_given_course or course["id"] != id):
                    student_work.extend(classes_dict[id])
                if not duplicates:
                    used_ids.append(id)
            except:
                pass
            #student_work.extend(student_dict[student_id])
    new_student_work = []
    for assignment in student_work:
        if "dueDate" in assignment:
            if check_greater(assignment["dueDate"], min_date) and check_less(assignment["dueDate"], max_date):
                new_student_work.append(assignment)
    if not duplicates:
        new_without_duplicates = []
        title_dict = {}
        for assignment in new_student_work:
            if assignment["title"] not in title_dict:
                title_dict[assignment["title"]] = []
                new_without_duplicates.append(assignment)
                title_dict[assignment["title"]].append(assignment["dueDate"])
            elif assignment["dueDate"] not in title_dict[assignment["title"]]:
                new_without_duplicates.append(assignment)
                title_dict[assignment["title"]].append(assignment["dueDate"])
        return new_without_duplicates
    return new_student_work

def check_greater(due_date, min_date):
    return (due_date["year"] > min_date["year"]) or ((due_date["year"] == min_date["year"]) and (due_date["month"] > min_date["month"])) or ((due_date["year"] == min_date["year"]) and (due_date["month"] == min_date["month"]) and (due_date["day"] >= min_date["day"]))

def check_less(due_date, max_date):
    return (due_date["year"] < max_date["year"]) or ((due_date["year"] == max_date["year"]) and (due_date["month"] < max_date["month"])) or ((due_date["year"] == max_date["year"]) and (due_date["month"] == max_date["month"]) and (due_date["day"] <= max_date["day"]))

def course_id_from_enrollment_code(courses, code):
    course_id = None
    for course in courses:
        try:
            if course["enrollmentCode"] == code:
                course_id = course["id"]
                break
        except: pass
    return course_id

initialize()
COURSES = get_courses()
#gc.collect()
#print("done")
#get_coursework(COURSES)
get_old_coursework_data()
#gc.collect()
print("complete")
#get_all_course_schedule(get_courses(COURSES))
courseid = course_id_from_enrollment_code(COURSES, 'h5krglq')
print(courseid)
print(get_single_course_schedule(COURSES, courseid, duplicates=True, include_given_course=True, min_date={'year': 2021, 'month': 5, 'day': 1}, max_date={'year': 2021, 'month': 5, 'day': 31}))