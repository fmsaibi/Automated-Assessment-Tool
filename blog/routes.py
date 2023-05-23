import json

from flask import render_template, url_for, request, redirect, flash, session, session
from blog import app, db, calculator
from blog.models import User, Question, Assessment_list
from blog.forms import LoginForm, RegistrationForm, LogoutForm, ForgetPWForm, ResetPWForm, QuestionForm
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

@app.route("/")
# ------ Login --------------------------------------------------------------------------------------------------------
@app.route("/login/", methods=['POST'])
def login():
    form = LoginForm()
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    else:
        if request.method == 'POST':
            if form.validate_on_submit():
                user = User.query.filter_by(email=form.email.data).first()
                if user is not None and user.verify_password(form.password.data):
                    login_user(user)
                    flash('Login Successful', 'success')
                    return redirect(url_for('home'))
                else:
                    flash('Invalid email or password', 'danger')
                    return render_template('login.html', form=form)

        return render_template('login.html', form=form)


# ------Home Page-------------------------------------------------------------------------------------------------------
# Acess to First Page of AAT page
@app.route("/home/")
@login_required
def home():
    return redirect(url_for('assessement'))


# ------Assessement Page-------------------------------------------------------------------------------------------------
# Acess to First Page of AAT page
@app.route("/assessement/")
@login_required
def assessement():
    return render_template('assessement.html', title='Assessement')


# ------Question List Page-------------------------------------------------------------------------------------------------
# Acess to First Page of AAT page
@app.route("/assessement/question/", methods=['GET', 'POST'])
@login_required
def question():
    form = QuestionForm()
    questions = Question.query.join(User, Question.initiator == User.id).with_entities(Question.id, Question.question,
                                                                                       Question.category,
                                                                                       Question.module_code,
                                                                                       Question.created_date, \
                                                                                       Question.modify_date,
                                                                                       Question.answers, Question.level,
                                                                                       Question.points, User.first_name, \
                                                                                       User.last_name,
                                                                                       Question.tags).order_by(
        Question.created_date.desc()).all()

    return render_template('question.html', title='Questions', current_user=current_user, form=form,
                           questions=questions)


# ------Add Question -------------------------------------------------------------------------------------------------
# Acess to First Page of AAT page
@app.route("/assessement/question/add_question/", methods=['GET', 'POST'])
@login_required
def add_question():
    form = QuestionForm()
    success = False

    if request.method == 'POST':
        result_dict = {}
        checkmark = []
        answers = []
        tags = request.form.get('tags')

        if form.category.data == "single":
            answers = request.form.getlist('mysingletext')
            checkmark = request.form.getlist('mysinglebox')

        elif form.category.data == "multiple":
            answers = request.form.getlist('mymultipletext')
            checkmark = request.form.getlist('mymultiplebox')

        if checkmark:
            # Convert the array to dictionary
            for i, answer in enumerate(answers, 1):
                if str(i) in checkmark:
                    result_dict["{}".format(answer)] = True
                else:
                    result_dict["{}".format(answer)] = False

            if form.validate_on_submit():
                try:
                    newQuestion = Question(module_code=form.module_code.data, question=form.question.data,
                                           answers=result_dict, initiator=int(current_user.id),
                                           category=form.category.data, level=form.level.data, points=form.points.data,
                                           tags=tags)
                    db.session.add(newQuestion)
                    db.session.commit()
                    form.question.data = ""
                    form.category.data = ""
                    form.module_code.data = ""
                    checkmark.clear()
                    answers.clear()
                    newQuestion = ""
                    success = True
                    return render_template('add_question.html', title='Questions', form=form, success=success)
                except:
                    db.session.rollback()

    return render_template('add_question.html', title='Questions', form=form, success=success)


# ------Edit Question -------------------------------------------------------------------------------------------------
# Acess to First Page of AAT page
@app.route("/assessement/question/edit_question/<question_id>/", methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    form = QuestionForm(obj=question)

    if request.method == 'POST':

        result_dict = {}
        checkmark = []
        answers = []
        tags = request.form.get('tags')

        if form.category.data == "single":
            answers = request.form.getlist('mysingletext')
            checkmark = request.form.getlist('mysinglebox')

        elif form.category.data == "multiple":
            answers = request.form.getlist('mymultipletext')
            checkmark = request.form.getlist('mymultiplebox')

        if checkmark:
            # Convert the array to dictionary
            for i, answer in enumerate(answers, 1):
                if str(i) in checkmark:
                    result_dict["{}".format(answer)] = True
                else:
                    result_dict["{}".format(answer)] = False

        question.question = form.question.data
        question.points = form.points.data
        question.level = form.level.data
        question.module_code = form.module_code.data
        question.category = form.category.data
        question.answers = result_dict
        question.tags = tags
        if form.validate_on_submit():
            try:
                db.session.commit()
                flash('Successful updated!', 'success')
                return render_template('edit_question.html', title='Editing Questions', form=form, questions=question)
            except:
                flash('Error: couldnt not update', 'danger')
                db.session.rollback()

    form.question.default = question.question
    form.level.default = question.level
    form.points.default = question.points
    form.module_code.default = question.module_code
    form.category.default = question.category
    form.process()

    return render_template('edit_question.html', title='Editing Questions', form=form, questions=question,
                           current_user=current_user)


# ------Assessment Choosing Page-------------------------------------------------------------------------------------------------
@app.route("/assessement/question/create_assessment")
def create_assessment():
    return render_template('create_assessment.html', title='Assessments')


# ------ Formative Assessment Creation Page-------------------------------------------------------------------------------------------------
@app.route("/assessement/question/create_assessment/formative_assessment/")
def formative_assessment():
    # questions=Question.query.all()
    # for eachQ in questions:
    #   for eachAn in eachQ.answers:
    #     print(eachAn)
    return render_template('formative_assessment.html', title='Formative')


# ------ Formative Assessment filters Page-------------------------------------------------------------------------------------------------
@app.route("/assessement/question/create_assessment/formative_assessment/filters", methods=['GET', 'POST'])
def filters():
    # Get the selected options from the form data
    module = request.form['module-select']
    category = request.form['category-select']

    # Construct the SQLAlchemy query
    query = Question.query
    if module:
        query = query.filter(Question.module_code == module)
        if category == "Both":
            query = query.filter(Question.category.in_(["single", "multiple"]))
        elif category == "Single":
            query = query.filter(Question.category == "single")
        elif category == "Multiple":
            query = query.filter(Question.category == "multiple")

    # Retrieve the filtered data

    filters = query.all()
    form = QuestionForm

    return render_template('filters.html', filters=filters, form=form)


# ------ Formative Assessment Question Template-------------------------------------------------------------------------------------------------
# @app.route("/assessement/question/create_assessment/formative_assessment/filters/",methods=['GET','POST'])
# def questiontemplate():
#     form=QuestionForm
#     if request.method == 'POST':
#       session["data"] = request.form.getlist('set-question')

#       return redirect(url_for('question_template'))
#     return render_template('filters.html', filters=filters,form=form)


@app.route("/assessement/question/create_assessment/formative_assessment/filters/", methods=['GET', 'POST'])
def questiontemplate():
    form = QuestionForm

    if request.method == 'POST':
        values = request.form.getlist('set-question')
        session["data"] = request.form.getlist('set-question')

        values_str = json.dumps(values)
        new_item = Assessment_list(list=values_str)
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('question_template'))
    return render_template('filters.html', filters=filters, form=form)


@app.route("/question_template/", methods=['GET', 'POST'])
@login_required
def question_template():
    id_list = session.get("data", None)
    questions = Question.query.filter(Question.id.in_(id_list)).all()
    form = QuestionForm()
    return render_template('assessment_template.html', title='Question Template', questions=questions, form=form)


# ------User Profile------------------------------------------------------------------------------------------------------
@app.route("/profile/")
@login_required
def profile():
    return render_template('profile.html', title='Profile', current_user=current_user)


# ------Create Dummy Account --------------------------------------------------------------------------------------------
# Available only to Developer and Admin Accounts
@app.route("/register/", methods=['GET', 'POST'])
@login_required
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            User()
            user = User(first_name=form.first_name.data,
                        last_name=form.last_name.data,
                        access_type=form.access_type.data,
                        hashed_password=generate_password_hash(form.password.data),
                        email=form.email.data,
                        initiator=int(current_user.id))
            db.session.add(user)
            db.session.commit()
            form.first_name.data = ""
            form.last_name.data = ""
            form.access_type.data = "Select"
            form.password.data = ""
            form.email.data = ""
            flash('New user successfully Register', 'success')
            redirect(url_for('users'))
        except:
            db.session.rollback()
            flash('Error, Could not register, Please try agin.', 'danger')
    return render_template('register.html', title='Register', form=form)


# ------Logout---------------------------------------------------------------------------------------------------------
@app.route("/logout")
@login_required
def logout():
    try:
        logout_user()
        return redirect(url_for('login'))
    except:
        flash('Error', 'danger')


# ------Registred Users -----------------------------------------------------------------------------------------------
# Show  list of Dummy account
# Access is only valid to Admin and Developer
@app.route("/users/", methods=['GET', 'POST'])
@login_required
def users():
    if current_user.is_authenticated and current_user.access_type == 'admin' or current_user.access_type == 'developer':
        form = RegistrationForm()
        try:
            users = User.query.filter_by(initiator=current_user.id)
            return render_template('users.html', title='Users', form=form, users=users)
        except:
            flash('Error: couldnt loard user table', 'danger')


# ------allow user to reset password -----------------------------------------------------------------------------------------------
# Send password reset email with token
def send_reset_pw_mail(user):
    token = user.get_token()
    msg = Mail(
        from_email=app.config['MAIL_USERNAME'],
        # avoid being treated as spam, send pw reset email to specific email instead of the user account.
        to_emails='chensun_2017@126.com',
        subject="Password Reset Email",
        html_content=f'''Hi {user.first_name},\n
  In order to reset your account password, please follow the link below:\n
  {url_for("reset", token=token, _external=True)}\n
  <strong>Please note: this link will be valid for only one hour!</strong>\n
  If you did not request to reset password. please ignore this mail.'''
    )
    sg = SendGridAPIClient(os.environ.get('SG_API'))
    response = sg.send(msg)


# User clicked 'forget password'
@app.route('/reset', methods=['GET', 'POST'])
def forget():
    form = ForgetPWForm()
    form.validate_on_submit()
    if request.method == 'POST':
        email = form.email.data
        reset_user = User.query.filter_by(email=email).first()
        if not reset_user:
            flash('This email does not exist, please double check', 'danger')
            return redirect(url_for('login'))
        else:
            send_reset_pw_mail(reset_user)
            flash('Reset password email has been sent, please check your mail', 'success')
            return redirect(url_for('home'))
    return render_template('forget_pw.html', form=form)


# ------Allow user to enter new password---------------------------------------------------------------------------------
# User entered correct link
@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset(token):
    reset_user = User.verify_token(token)
    if reset_user == None:
        flash('Something went wrong, please log in your account')
        return redirect(url_for('home'))
    reset_form = ResetPWForm()
    reset_form.validate_on_submit()
    if request.method == 'POST':
        if reset_form.password.data != reset_form.confirm_password.data:
            flash('Your confirm password does not match your password. please re-enter.', 'danger')
            return redirect(url_for('reset', token=token))
        reset_user.hashed_password = generate_password_hash(reset_form.password.data)
        db.session.commit()
        login_user(reset_user)
        flash('Your password has been changed successfully', 'success')
        return redirect(url_for('home'))
    return render_template('reset_pw.html', form=reset_form, user=reset_user)


# ------Delete Account---------------------------------------------------------------------------------------------------
# Delete Dummy Account
# Access is only valid to Admin or Developer
@app.route("/delete/<option>/<int:id>/", methods=['GET', 'POST'])
@login_required
def delete(id, option):

  if option == "user":
    if current_user.is_authenticated and current_user.access_type == 'admin' or  current_user.access_type == 'developer':
        user_to_delete = User.query.get_or_404(id)
        try:
          db.session.delete(user_to_delete)
          db.session.commit()
          flash('Successful Deleted!', 'success')
          return redirect(url_for('users'))
        except:
          flash('Error: Couldnt delete the account', 'danger')
  elif option == "question":
        question_to_delete = Question.query.get_or_404(id)
        try:
          db.session.delete(question_to_delete)
          db.session.commit()
          flash('Successful Deleted!', 'success')
          return redirect(url_for('question'))
        except:
            flash('Error: Couldnt Delete Question', 'danger')
            return redirect(url_for('edit_question', question_id=id))


# ------Invalid URL-----------------------------------------------------------------------------------------------------
@app.errorhandler(404)
def page_not_found(error):
    return 'Error 404: Page not Found', 404


# ------Internel Server Error-----------------------------------------------------------------------------------------------------
# This route will display the internel server error
@app.errorhandler(500)
def internel_server_error(error):
    return render_template('500.html'), 500
