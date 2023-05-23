import random

from flask import render_template, jsonify, send_file
from blog import app, db, reports_routes
from blog.models import Assessment, Question, Attempts, Module_list, User, Module, db, Assessment_view
import pandas as pd
from io import BytesIO
import json
import datetime

explanations = ["The 'float()' function in Python is used to convert a number or a string that represents a number to a floating-point number.",
                "Bootstrap is not a database management system. It is a popular front-end framework used for building responsive websites.",
                "API stands for Application Programming Interface. It is a set of protocols, routines, and tools used for building software applications.",
                "The command used to initialize a Git repository in a directory is 'git init'.",
                "The keyword used to define a class in Java is 'class'.",
                "The 'bool' data type is used to represent Boolean values in Python. The two possible values are 'True' and 'False'.",
                "PHP, Python, and Node.js are examples of server-side programming languages. They are used for writing code that runs on a web server and generates dynamic web pages.",
                "Functions can be defined using Node.js using the 'function' keyword.",
                "The 'Scanner' class is used to read user input from the console in Java.",
                "Valid control statements in Java include 'if', 'else', 'for', 'while', 'do-while', 'switch', and 'break'. These statements are used to control the flow of execution in a Java program."]


def json_to_series(text):
    return pd.Series(text.values(), index=text.keys())


def process_assessment_data(a_id):
    """return data to download as CSV file"""
    query = db.session.query(Attempts, User).join(User, Attempts.uid == User.id)
    found_attempts = query.filter(Attempts.assessment_id == a_id).all()
    due_time = Assessment.query.get(a_id).start_date
    if Assessment.query.get(a_id).is_formative:
        attempts_data = [(a.id, a.uid, f"{u.first_name} {u.last_name}", a.created_date.strftime("%d %B %Y %H:%M"),
                          a.time_of_change - a.created_date, a.marks, a.feedback, a.student_answers) for a, u in found_attempts]
    else:
        attempts_data = [(a.id, a.uid, f"{u.first_name} {u.last_name}", a.created_date.strftime("%d %B %Y %H:%M"),
                          a.created_date - due_time, a.marks, a.feedback, a.student_answers) for a, u in found_attempts]
    df_data = pd.DataFrame(attempts_data, columns=['attempt_id', 'student_id', 'student_name', 'submission time',
                                                   'time spent', 'marks', 'feedback', 'answers'])
    question_ids = list(Assessment.query.get(a_id).question_id_score.keys())
    df_json = pd.concat([df_data, df_data['answers'].apply(json_to_series)], axis=1)
    for question in question_ids:
        len_of_columns = len(df_json.columns)
        df_json = pd.concat([df_json, df_json[question].apply(pd.Series)], axis=1)
        for i in range(len(df_json[question][0])):
            df_json.rename(columns={df_json.columns[len_of_columns]: question + "." + df_json.columns[len_of_columns]},
                           inplace=True)
            len_of_columns += 1
        df_json.drop(question, axis=1, inplace=True)
    return BytesIO(df_json.to_csv(index=False).encode())


def process_attempts_data(a_id, u_id):
    """return a dictionary containing a student's all attempt details on an assessment
    {'40':{'duration':xx,'feedback': bla, 'wrong_questions':[], 'wrong_answers':[], 'h': True}, '50': {...}}"""
    feedback_for_all = ['Your performance fell below the expected standard.',
                        'You met the minimum requirements for passing the exam.',
                        'You have shown a good understanding of the course material.',
                        'Your work is of a very high standard, well done!']
    found_attempts = Attempts.query.filter_by(assessment_id=a_id, uid=u_id).all()
    attempt_details = {}
    h_score = 0
    for attempt in found_attempts:
        wrong_questions = []
        wrong_answers = []
        wrong_questions_numbers = []
        duration = int((attempt.time_of_change - attempt.created_date).total_seconds() / 60)
        if attempt.marks > h_score:
            h_score = attempt.marks
            h_id = attempt.id
        for question in attempt.student_answers:
            if attempt.student_answers[question] != Question.query.get(question).answers:
                wrong_questions.append(Question.query.get(question))
                options = list(attempt.student_answers[question].keys())
                wrong_options = [o for o in options if attempt.student_answers[question][o]]
                wrong_answers.append(wrong_options)
                wrong_questions_numbers.append(list(attempt.student_answers.keys()).index(question) + 1)
        grade = attempt.marks / sum(list(Assessment.query.get(a_id).question_id_score.values()))
        if grade < 0.5:
            feedback = feedback_for_all[0]
        elif grade < 0.65:
            feedback = feedback_for_all[1]
        elif grade < 0.9:
            feedback = feedback_for_all[2]
        else:
            feedback = feedback_for_all[3]
        attempt_detail = {
            'date': attempt.created_date.strftime("%d %B %Y"),
            'duration': duration,
            'feedback': feedback,
            'score': attempt.marks,
            'wrong_questions': wrong_questions,
            'wrong_questions_numbers': wrong_questions_numbers,
            'wrong_answers': wrong_answers,
        }
        attempt_details[attempt.id] = attempt_detail
    attempt_details[h_id]['h_score'] = True
    return attempt_details


def get_question_count_by_q_id(a_id, q_id):
    """return a dictionary that contains students' performance on a question within an assessment"""
    found_attempts = Attempts.query.filter_by(assessment_id=a_id).all()
    found_question = Question.query.get(q_id)
    content = found_question.question
    options = list(found_question.answers.keys())
    correct_options = [x for x in options if found_question.answers[x]]
    counts = []
    incorrect_times = 0
    for option in options:
        count = 0
        for attempt in found_attempts:
            if attempt.student_answers[q_id][option]:
                count += 1
        counts.append(count)
    for attempt in found_attempts:
        if attempt.student_answers[q_id] != found_question.answers:
            incorrect_times += 1
    count_data = {
        'id': q_id,
        'content': content,
        'correct_options': correct_options,
        'options': options,
        'count': counts,
        'incorrect_times': incorrect_times,
    }
    return count_data


def get_question_count(a_id):
    """return the distributions of each option for each question
    [{‘id’: 1, 'content: "XXX", ''options':[a, b, c], 'count': [6, 2, 2]}, ...] """
    found_assessment = Assessment.query.get(a_id)
    question_ids = list(found_assessment.question_id_score.keys())
    question_count = []
    for q_id in question_ids:
        question_count.append(get_question_count_by_q_id(a_id, q_id))
    return question_count


def get_assessment_overview(a_id):
    """return the distribution of all grades for Summative
    [['Fail', 'Pass', 'Merit', 'Distinction'], [2, 2, 2, 2]]"""
    found_attempts = Attempts.query.filter_by(assessment_id=a_id).all()
    found_assessment = Assessment.query.get(a_id)
    total_score = sum(list(found_assessment.question_id_score.values()))
    grades = ['Fail', 'Pass', 'Merit', 'Distinction']
    counts = []
    for grade in grades:
        count = 0
        for attempt in found_attempts:
            if reports_routes.grade(round(attempt.marks / total_score * 100)) == grade:
                count += 1
        counts.append(count)
    return [grades, counts]


def get_assessment_time(a_id):
    """return all time spent for Summative
    [[A, B, C], [00:10:00, 00:20:00, 00:30:00], ['10 mins', '20 mins', '30 mins']]"""
    query = db.session.query(Attempts, User).join(User, Attempts.uid == User.id)
    found_attempts = query.filter(Attempts.assessment_id == a_id).order_by(Attempts.created_date.asc()).all()
    students = []
    time = []
    time_label = []
    if not Assessment.query.get(a_id).is_formative:
        due_time = Assessment.query.get(a_id).start_date
        for a, u in found_attempts:
            students.append(f"{u.first_name} {u.last_name}")
            time.append(int((a.created_date - due_time).total_seconds() / 60))
            time_label.append(f"{int((a.created_date - due_time).total_seconds() / 60)} mins")
    else:
        for a, u in found_attempts:
            students.append(f"{u.first_name} {u.last_name}")
            time.append(int((a.time_of_change - a.created_date).total_seconds() / 60))
            time_label.append(f"{int((a.time_of_change - a.created_date).total_seconds() / 60)} mins")
    return [students, time, time_label]


def get_assessment_name(m_id, assess_id):
    assessment_ids = list(assessment.id for assessment in Assessment.query.filter_by(module_code=m_id).all())
    assessment_name = f"Assessment {assessment_ids.index(int(assess_id)) + 1}"
    return assessment_name


@app.route('/return_assessment_data_for_js/<a_id>')
def return_assessment_data_for_js(a_id):
    data = get_question_count(a_id)
    return jsonify(data)


@app.route('/return_assessment_overview_for_js/<a_id>')
def return_assessment_overview_for_js(a_id):
    grade_data = get_assessment_overview(a_id)
    time_data = get_assessment_time(a_id)
    data = {
        "grades": grade_data,
        "time": time_data,
    }
    return jsonify(data)


@app.route('/return_formative_individual/<a_id>/<u_id>')
def return_formative_individual(a_id, u_id):
    # attempt_detail = {
    #             'date': attempt.created_date.strftime("%d %B %Y"),
    #             'duration': duration,
    #             'feedback': feedback,
    #             'score': attempt.marks,
    #             'wrong_questions': wrong_questions,
    #             'wrong_questions_numbers': wrong_questions_numbers,
    #             'wrong_answers': wrong_answers,
    #         }
    attempt_detail = process_attempts_data(a_id, u_id)
    attempt_1_radar = [65, 32, 60, 70, 56, 40, 50, 45, 80]
    attempt_2_radar = [80, 60, 75, 70, 90, 100, 95, 85, 79]
    attempt_1 = random.sample(attempt_1_radar, 6)
    attempt_2 = random.sample(attempt_2_radar, 6)
    attempt_durations = []
    attempt_marks = []
    for detail in attempt_detail:
        attempt_durations.append(attempt_detail[detail]['duration'])
        attempt_marks.append(attempt_detail[detail]['score'])
    data = [attempt_durations, attempt_marks, attempt_1, attempt_2]
    return jsonify(data)


@app.route('/return_assessment_time_for_js/<a_id>')
def return_assessment_time_for_js(a_id):
    data = get_assessment_time(a_id)
    return jsonify(data)


# return CSV file to Chart.js
@app.route('/download_assessment_data/<a_id>')
def download_assessment_data(a_id):
    return send_file(process_assessment_data(a_id), mimetype='text/csv', download_name='CMT119_Assessment_1.csv')


@app.route('/formative_cohort_report/<m_id>/<a_id>')
def formative_cohort_report(m_id, a_id):
    query = db.session.query(Attempts, User).join(User, Attempts.uid == User.id)
    found_attempts = query.filter(Attempts.assessment_id == a_id).all()  # A list of (Attempt, User)
    found_module = Module_list.query.get(m_id)  # A single module
    assessment_name = get_assessment_name(m_id, a_id)
    found_assessment = Assessment.query.get(a_id)  # A single assessment
    total_score = sum(list(found_assessment.question_id_score.values()))
    question_ids = list(found_assessment.question_id_score.keys())
    question_count = []
    for q_id in question_ids:
        question_count.append(get_question_count_by_q_id(a_id, q_id)['incorrect_times'])
    students = [u for a, u in found_attempts]  # A list of Student class
    students = list(dict.fromkeys(students))  # A list of Student class(No duplicates)
    # A dictionary  {'student_id' : [[attempt1, attempt2, ...], [attempt_times, h_score, l_score]]}
    data_per_student = {}
    for s in students:
        s_attempts = []
        h_score = 0
        l_score = total_score
        for a, u in found_attempts:
            if a.uid == s.id:
                s_attempts.append(a)
                if a.marks > h_score:
                    h_score = a.marks
                if a.marks < l_score:
                    l_score = a.marks
        data_per_student[s.id] = [s_attempts, [len(s_attempts), h_score, int(l_score/10) - 3]]
    found_questions = [Question.query.get(q_id) for q_id in question_ids]  # A list of Question
    module = {
        'module_code': m_id,
        'module_name': found_module.module_name
    }
    for q in found_questions:
        print(q.question)
    return render_template('reports_templates/formative_cohort_report.html', assessment_name=assessment_name,
                           assessment=found_assessment, module=module, students=students, attempts=found_attempts,
                           data_per_student=data_per_student, questions=found_questions, question_count=question_count,
                           explanations=explanations)


@app.route('/formative_individual_report/<m_id>/<a_id>/<u_id>')
def formative_individual_report(m_id, a_id, u_id):
    assessment_name = get_assessment_name(m_id, a_id)
    found_module = Module_list.query.get(m_id)
    found_assessment = Assessment.query.get(a_id)
    found_student = User.query.get(u_id)
    found_attempts = Attempts.query.filter_by(assessment_id=a_id, uid=u_id).all()
    total_score = sum(list(found_assessment.question_id_score.values()))
    pass_score = round(total_score * 0.7, 2)
    distinction_score = round(total_score * 0.9, 2)
    assessment_details = {
        'name': assessment_name,
        'interval': ['50', '', '', ''],
        'grades': ['Fail', 'Pass', 'Merit', 'Distinction'],
        'total_score': total_score,
        'pass_score': pass_score,
        'd_score': distinction_score
    }
    attempts_details = process_attempts_data(a_id, u_id)
    return render_template('reports_templates/formative_individual_report.html', assessment=found_assessment,
                           student=found_student, attempts=found_attempts, assessment_details=assessment_details,
                           module=found_module, attempts_details=attempts_details, attempt_times=len(found_attempts),
                           explanations=explanations, )


# attempt_detail = {
#             'date': attempt.created_date.strftime("%d %B %Y"),
#             'duration': duration,
#             'feedback': feedback,
#             'wrong_questions': wrong_questions,
#             'wrong_questions_numbers': wrong_questions_numbers,
#             'wrong_answers': wrong_answers,
#         }