import json

from flask import render_template, Blueprint, flash, redirect, url_for, request
from flask_login import current_user, login_required, fresh_login_required
from sqlalchemy import func, exc

from blog import app, calculator
from blog.report_forms import FeedbackForm, MarkForm
import html

from blog.models import Assessment, Question, Attempts, Module_list, User, Module, db, Assessment_view

from blog.authorization import lecturer_required, student_required, lecturer_or_student_required

from datetime import datetime

rp = Blueprint("report", __name__, url_prefix="/reports")


@rp.route("/")
@login_required
@lecturer_required
def home():
    assessments = {}

    uid = current_user.id
    # modules = Module.query.filter_by(uid=uid).all()

    query = db.session.query(Module, Module_list).join(Module_list, Module.module_code == Module_list.module_code)
    query = query.filter(Module.uid == uid)
    modules = query.all()

    is_assessment_formative = {}

    for module, module_list in modules:
        assessments[module.module_code] = {}
        module_assessments = Assessment.query.filter_by(module_code=module.module_code)
        counter = 1
        for assessment in module_assessments:
            assessments[module.module_code][f'Assessment {counter}'] = assessment.id
            counter += 1
            if assessment.is_formative:
                is_assessment_formative[assessment.id] = True
            else:
                is_assessment_formative[assessment.id] = False

    # create a dictionary of URLs
    urls = {}
    for module_code in assessments:
        print(assessments[module_code])
        for assessment in assessments[module_code]:
            print(f'Module {module_code}')
            print(f'Assessment {assessment}')
            # generate the URL with the module_code and assessment_id arguments
            url = url_for("report.view_reports_list", module_code=module_code,
                          assessment_id=assessments[module_code][assessment])
            print(url)
            # use the module_code and assessment as the key for the URL
            key = f"{module_code}_{assessment}"
            # add the key and URL to the urls dictionary
            urls[key] = url

    assessments = json.dumps(assessments)
    urls = json.dumps(urls)
    is_assessment_formative = json.dumps(is_assessment_formative)
    assessments_urls = {'assessments': assessments, 'urls': urls, 'is_assessment_formative': is_assessment_formative}
    # pass the urls dictionary to the template

    return render_template("reports_templates/modules.html", assessments_urls=assessments_urls, modules=modules)


# Also wrap with a lecturer required for now
@rp.route("/<string:module_code>/<int:assessment_id>/")
@login_required
@lecturer_required
def view_reports_list(module_code, assessment_id):
    # Check viewing privileges for the report to be viewed using enrollment (module table)
    lecturer_in_module = Module.query.filter_by(uid=current_user.id, module_code=module_code).first()
    found_module = Module_list.query.get(module_code)
    if lecturer_in_module:
        #     Obtain all attempts for the assessment_id
        query = db.session.query(Attempts, User).join(User, Attempts.uid == User.id)
        query = query.filter(Attempts.assessment_id == assessment_id, Attempts.module_code == module_code)
        attempts = query.all()

        assessment = Assessment.query.filter_by(module_code=module_code, id=assessment_id).first()
        assessment_name = \
            Assessment_view.query.with_entities(Assessment_view.assessment_name).filter_by(id=assessment_id).first()[0]
        max_score = 0
        if assessment:
            if assessment.is_formative:
                return redirect(url_for('formative_cohort_report', m_id=module_code, a_id=assessment_id))
            for question in assessment.question_id_score:
                question_points = Question.query.filter_by(
                    id=question).first().points or assessment.question_id_score[question]
                max_score += question_points
            q_ids = list(assessment.question_id_score.keys())
            found_qs = [Question.query.get(q_id) for q_id in q_ids]
            q_count = [calculator.get_question_count_by_q_id(assessment_id, q_id)['incorrect_times'] for q_id in q_ids]
        else:
            pass

        pass_score = round(max_score / 2)
        print(max_score)
        print(pass_score)

        return render_template("reports_templates/module_assessment_reports.html", attempts=attempts, pass_score=pass_score,
                               module_code=module_code, module=found_module, assessment=assessment,
                               assessment_name=assessment_name, questions=found_qs, count=q_count)

    else:
        flash("Lecturer not enrolled in this module.")
        return redirect(url_for('routes.home'))


# Wrap this with a fresh login required
# Check lecturer or student is enrolled in the module
# If student, check uid on report is same as user's session id
@rp.route("/view_report/<string:module_code>/<int:assessment_id>/<int:uid>/", methods=("GET", "POST"))
@login_required
@fresh_login_required
@lecturer_or_student_required
def view_summative_report(module_code, assessment_id, uid):
    user_in_module = Module.query.filter_by(uid=current_user.id, module_code=module_code).first()
    attempt = Attempts.query.filter_by(module_code=module_code, assessment_id=assessment_id, uid=uid).first()
    assessment = Assessment.query.filter_by(id=assessment_id).first()
    if assessment.is_formative:
        return redirect(url_for('formative_individual_report', m_id=module_code, a_id=assessment_id, u_id=uid))
    module = Module_list.query.filter_by(module_code=module_code).first()
    # Check viewing privileges for the report to be viewed using enrollment (module table)
    if user_in_module or current_user.id == attempt.uid:
        is_lecturer = User.query.filter_by(id=current_user.id, access_type='lecturer').first()
        student = User.query.filter_by(id=uid).first()
        assessment_name = \
            Assessment_view.query.with_entities(Assessment_view.assessment_name).filter_by(id=assessment_id).first()[0]
        submission_date = attempt.created_date.strftime("%d %B %Y at %H:%M:%S")
        due_date = assessment.end_date.strftime("%d %B %Y at %H:%M:%S")
        # Check that the report can now be viewed (past due date) for summative assessment
        if (datetime.utcnow() > assessment.end_date and not assessment.is_formative) or assessment.is_formative:
            global student_attempt_percentile
            lecturer_id = attempt.lecturer_id
            if lecturer_id:
                lecturer = User.query.filter_by(id=lecturer_id).first()
                lecturer_name = lecturer.first_name + " " + lecturer.last_name
                update_date = attempt.time_of_change.strftime("%d %B %Y, %H:%M:%S")
                mark_change_reason = attempt.mark_change_reason
            else:
                lecturer_name = None
                update_date = None
                mark_change_reason = None

            assessment_questions = assessment.question_id_score
            student_answers = attempt.student_answers

            # Initialize questions dictionary
            questions = {}
            q_number = 1  # This is the questions number used when displaying the questions in the report
            marks_available_for_all_questions = []
            marks_obtained_for_all_questions = []
            question_categories = {}  # Stores data related to question categories for the assessment
            marks_available_for_categories = {}  # Stores marks available for each category of questions
            """
                Initialize and populate questions dictionary with question details
                including the question, the correct answers, the student's answers and marks for the question
                """
            for q_id in assessment_questions:
                questions[q_number] = {}
                question_row = Question.query.filter_by(id=q_id).first()
                question = question_row.question
                correct_answers = question_row.answers
                questions[q_number]["Q"] = question
                questions[q_number]["correct_answers"] = correct_answers
                questions[q_number]["student_answers"] = student_answers[q_id]

                # Add marks available for category question to list
                marks_available_for_question = question_row.points or assessment_questions[q_id]
                marks_available_for_all_questions.append(marks_available_for_question)

                # Add new categories when encountered in new questions
                if question_row.category not in question_categories:
                    question_categories[question_row.category] = []
                if question_row.category not in marks_available_for_categories:
                    marks_available_for_categories[question_row.category] = []

                marks_available_for_categories[question_row.category].append(marks_available_for_question)
                # Add marks obtained for category question to list
                if student_answers[q_id] == correct_answers:
                    marks_obtained_for_all_questions.append(marks_available_for_question)
                    questions[q_number]["marks_for_question"] = marks_available_for_question
                    question_categories[question_row.category].append(marks_available_for_question)

                else:
                    marks_obtained_for_all_questions.append(0)
                    questions[q_number]["marks_for_question"] = 0
                    question_categories[question_row.category].append(0)

                questions[q_number]["marks_available_for_question"] = marks_available_for_question
                q_number = q_number + 1

            total_available_marks = sum(marks_available_for_all_questions)
            total_obtained_marks = sum(marks_obtained_for_all_questions)

            # Add mark to db if it is not there
            if not attempt.marks:
                attempt.marks = total_obtained_marks
                db.session.commit()

            student_mark = attempt.marks
            # Get feedback
            if attempt.feedback:
                pass
            else:
                # generate feedback based on performance in different categories
                generated_feedback = feedback_by_categories(marks_available_for_categories, qualitative_statement,
                                                            question_categories, total_available_marks, student_mark)
                generated_feedback = convert_newlines_to_html_paragraphs(generated_feedback)
                generated_feedback = html.unescape(generated_feedback)
                attempt.feedback = generated_feedback
                db.session.commit()

            form = FeedbackForm()
            form.feedback.default = attempt.feedback
            mark_form = MarkForm()

            # fetch student's mark percentile
            data = Attempts.query.with_entities(Attempts.uid,
                                                func.percent_rank().over(order_by=Attempts.marks)).filter_by(
                assessment_id=assessment_id).all()
            for student_id, percentile in data:
                if student_id == uid:
                    student_attempt_percentile = percentile

            prcnt = round(student_attempt_percentile * 100)

            def get_suffix(prcnt):
                # convert percentile to integer
                prcnt = int(prcnt)
                # check the last digit of percentile
                last_digit = prcnt % 10
                # check the second last digit of percentile
                second_last_digit = (prcnt // 10) % 10
                # if the second last digit is 1, the suffix is always "th"
                if second_last_digit == 1:
                    return "th"
                # otherwise, the suffix depends on the last digit
                elif last_digit == 1:
                    return "st"
                elif last_digit == 2:
                    return "nd"
                elif last_digit == 3:
                    return "rd"
                else:
                    return "th"

            assessment_details = {'assessment': assessment_name,
                                  'code': assessment.id,
                                  'submission_time': submission_date,
                                  'due_time': due_date,
                                  'marks': attempt.marks,
                                  'percentile': f'{prcnt}<sup>{get_suffix(prcnt)}</sup> percentile',
                                  'passmark': round(total_available_marks / 2),
                                  'total': total_available_marks}
            enrolment_details = {'module_name': module.module_name,
                                 'code': module.module_code,
                                 'student': student.first_name + " " + student.last_name,
                                 'student_id': student.id
                                 }

            return render_template('reports_templates/feedback_report.html', form=form, markForm=mark_form,
                                   questions=questions,
                                   attempt_id=attempt.id,
                                   lecturer_name=lecturer_name,
                                   lecturer=is_lecturer,
                                   update_date=update_date,
                                   mark_change_reason=mark_change_reason,
                                   enrolmentDetails=enrolment_details,
                                   assessmentDetails=assessment_details, generatedFeedback=attempt.feedback)
        else:
            flash(f'This report will only be available to view after {due_date}', "message")
            return redirect(url_for('report.home'))
    else:
        flash("This user is not authorized to view this report.", "message")
        return redirect(url_for('routes.home'))


@rp.route('/update_marks/<int:attempt_id>', methods=['GET', 'POST'])
@login_required
@fresh_login_required
@lecturer_required
def update_marks(attempt_id):
    form = MarkForm()
    attempt = Attempts.query.get_or_404(attempt_id)
    if form.validate_on_submit():
        if form.marks.data:
            try:
                attempt.marks = form.marks.data  # Update marks column
                new_reason = form.reason.data.replace(' data-placeholder="Please provide a reason for the change."', '')
                new_reason = new_reason.replace('<p>', '')
                new_reason = new_reason.replace('</p>', '')
                attempt.mark_change_reason = new_reason  # Update the reason for changing the mark

                attempt.lecturer_id = current_user.id  # Update details of staff that changed the mark
                db.session.commit()
                flash("marks updated")

            except exc.IntegrityError:
                # handle integrity error, such as unique constraint violation
                db.session.rollback()
                flash('Error, Could not process. Please try again.')

            except exc.DatabaseError:
                # handle generic database error, such as connection failure
                db.session.rollback()
                flash('Error, Could not connect to the database.')

            except exc.SQLAlchemyError:
                # handle any other SQLAlchemy error
                db.session.rollback()
                flash('Error, Something went wrong with SQLAlchemy.')

    return redirect(
        url_for('report.view_summative_report', module_code=attempt.module_code, assessment_id=attempt.assessment_id,
                uid=attempt.uid))


@rp.route('/update_feedback/<int:feedback_id>', methods=['GET', 'POST'])
@login_required
@fresh_login_required
@lecturer_required
def update_feedback(feedback_id):
    form = FeedbackForm()
    attempt = Attempts.query.get_or_404(feedback_id)
    if form.validate_on_submit():
        #     enter marks in db
        if form.feedback.data:
            try:
                attempt.feedback = form.feedback.data  # Update marks column
                db.session.commit()
                flash("Feedback updated.")

            except exc.IntegrityError:
                # handle integrity error, such as unique constraint violation
                db.session.rollback()
                flash('Error, Could not process. Please try again.')

            except exc.DatabaseError:
                # handle generic database error, such as connection failure
                db.session.rollback()
                flash('Error, Could not connect to the database.')


            except exc.SQLAlchemyError:
                # handle any other SQLAlchemy error
                db.session.rollback()
                flash('Error, Something went wrong with SQLAlchemy.')

    return redirect(
        url_for('report.view_summative_report', module_code=attempt.module_code, assessment_id=attempt.assessment_id,
                uid=attempt.uid))


def feedback_by_categories(marks_available_for_categories, qualitative_statement_fn,
                           question_categories, total_available_marks, student_mark,
                           dict_for_category_comparison_by_percentage=None):
    global worse_category, worse_category_marks, dict_for_category_comparison_by_marks, categories_comparison
    if dict_for_category_comparison_by_percentage is None:
        dict_for_category_comparison_by_percentage = {}
        dict_for_category_comparison_by_marks = {}
    categories_summary = f'<b>Grade: {grade(round(student_mark / total_available_marks * 100))}</b>\n\n'
    for category in question_categories:
        number_of_questions_in_category = len(question_categories[category])
        marks_from_qs_in_category = sum(question_categories[category])
        number_of_qs_gotten_correct_in_category = len([i for i in question_categories[category] if i != 0])
        category_total_marks = sum(marks_available_for_categories[category])
        percentage_of_correct_questions = round(
            number_of_qs_gotten_correct_in_category / number_of_questions_in_category * 100)
        percentage_of_category_marks_obtained = round(marks_from_qs_in_category / category_total_marks * 100)
        dict_for_category_comparison_by_marks[category] = marks_from_qs_in_category
        dict_for_category_comparison_by_percentage[category] = percentage_of_category_marks_obtained

        categories_summary += f'<b>' \
                              f'{category.capitalize()} choice questions</b>\n' \
                              f'For the category {category} choice questions, ' \
                              f'there were {number_of_questions_in_category} total questions. ' \
                              f'Of these, you got {number_of_qs_gotten_correct_in_category} correct ' \
                              f'({percentage_of_correct_questions}%). ' \
                              f'In total, there were {category_total_marks} marks available for this category and ' \
                              f'you obtained {marks_from_qs_in_category} marks ' \
                              f'({percentage_of_category_marks_obtained}%). ' \
                              f'You ' \
                              f'{qualitative_statement_fn(percentage_of_category_marks_obtained)} ' \
                              f'in this category. \n\n' \

    categories_comparison = f'<b>Conclusion</b>\n\n'
    if len(question_categories) > 1:
        my_dict = dict_for_category_comparison_by_percentage
        my_dict_marks = dict_for_category_comparison_by_marks
        max_value = max(my_dict.values())
        max_value_marks = max(my_dict_marks.values())
        better_category = None
        better_category_marks = None
        max_keys = [key for key, value in my_dict.items() if value == max_value]
        max_keys_marks = [key for key, value in my_dict_marks.items() if value == max_value_marks]
        # Only add this feedback if student performed better at one of the categories
        if len(max_keys) == 1:
            for key in my_dict:
                if my_dict[key] == max_value:
                    better_category = key
                else:
                    worse_category = key
            # if worse_category%
            categories_comparison += f'You performed better at ' \
                                     f'{better_category} choice questions by percentage of marks obtained in category. '
            if len(max_keys_marks) == 1:
                for key in my_dict_marks:
                    if my_dict_marks[key] == max_value_marks:
                        better_category_marks = key
                    else:
                        worse_category_marks = key
                if student_mark < total_available_marks:
                    categories_comparison += f'Most of your marks came from ' \
                                             f'{better_category_marks} choice questions. ' \
                        # f'you are encouraged to practice more {worse_category} choice questions.'
            if my_dict[worse_category] < 50:
                categories_comparison += f'Practice more {worse_category} choice questions. '

            categories_comparison += f'Overall, you {qualitative_statement_fn(round(student_mark / total_available_marks * 100))} ' \
                                     f'in this assessment. '

        else:
            categories_comparison += f'Overall, you performed equally well in both categories by percentage of questions correct in each category and '
            if student_mark < 0.5 * total_available_marks:
                categories_comparison += f'are encouraged to continue practicing both types of questions. ' \
                                         f'Refer to the question answers below to see where you could have improved.'
            else:
                categories_comparison += f'{qualitative_statement_fn(round(student_mark / total_available_marks * 100))}' \
                                         f' in the assessment. ' \
                                         f'Keep practicing to continue doing well and get even better.'

        categories_summary += categories_comparison

    else:
        categories_summary += f'You {qualitative_statement_fn(round(student_mark / total_available_marks * 100))} ' \
                              f'in this assessment. '
        if student_mark < 0.5 * total_available_marks:
            categories_comparison += f'Refer to the question answers below for the correct answers.'
            categories_summary += categories_comparison

    return categories_summary


def convert_newlines_to_html_paragraphs(text):
    text = text.replace('\r\n', '\n')
    text = text.replace('\n\n', '\n')
    paragraphs = text.split('\n')
    html_paragraphs = []
    for paragraph in paragraphs:
        html_paragraphs.append(f'<p>{html.escape(paragraph)}</p>')
    return '\n'.join(html_paragraphs)


def qualitative_statement(percentage):
    return 'excelled' if percentage >= 70 else 'did really well' if percentage >= 60 else 'performed well' if percentage >= 50 else 'could have improved your performance'


def grade(percentage):
    return 'Distinction' if percentage >= 70 else 'Merit' if percentage >= 60 else 'Pass' if percentage >= 50 else 'Fail'


app.register_blueprint(rp)
