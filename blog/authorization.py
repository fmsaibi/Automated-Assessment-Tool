from functools import wraps
from flask_login import current_user
from flask import redirect, url_for, flash


def lecturer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and current_user.access_type == 'lecturer':
            return f(*args, **kwargs)
        else:
            flash("Access denied. Only lecturers allowed access.", 'message')
            return redirect(url_for('login'))

    return decorated_function


def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and current_user.access_type == 'student':
            return f(*args, **kwargs)
        else:
            flash("Access denied. Only students allowed access.", 'message')
            return redirect(url_for('login'))

    return decorated_function


def lecturer_or_student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and (current_user.access_type=='lecturer' or current_user.access_type=='student'):
            return f(*args, **kwargs)
        else:
            flash("Access denied. Only students and lecturers allowed access.", 'message')
            return redirect(url_for('login'))

    return decorated_function

