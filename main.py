from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Test, Question, TestResult, StudentAnswer, Class
from forms import RegistrationForm, LoginForm, CreateTestForm, QuestionForm
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'x7K9mP2nQ5rT8wY3zA6cV1bN4mF7jH9kL2cX5zB8nM1qW4eR6tY9uI3oP'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/img/'

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()


def calculate_grade(percentage):
    if percentage >= 90:
        return 5
    elif percentage >= 70:
        return 4
    elif percentage >= 50:
        return 3
    else:
        return 2


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        if current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
        else:
            return redirect(url_for('teacher_dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            username=form.username.data,
            password=hashed_password,
            role=form.role.data,
            level=1
        )
        if form.role.data == 'teacher':
            user.teacher_code = form.teacher_code.data

        if form.role.data == 'student':
            user.class_level = int(form.class_level.data)
            user.class_letter = form.class_letter.data

        db.session.add(user)
        db.session.commit()
        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember_me.data)
            if user.role == 'student':
                return redirect(url_for('student_dashboard'))
            else:
                return redirect(url_for('teacher_dashboard'))
        else:
            flash('Неверный логин или пароль', 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('teacher_dashboard'))

    tests = Test.query.all()
    completed_tests = TestResult.query.filter_by(student_id=current_user.id).all()
    completed_test_ids = [result.test_id for result in completed_tests]

    return render_template('student_dashboard.html',
                           tests=tests,
                           completed_test_ids=completed_test_ids,
                           level=current_user.level)


@app.route('/teacher_dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        return redirect(url_for('student_dashboard'))

    return render_template('teacher_dashboard.html')


@app.route('/add_questions/<int:q_num>', methods=['GET', 'POST'])
@login_required
def add_questions(q_num):
    if current_user.role != 'teacher':
        return redirect(url_for('student_dashboard'))

    form = QuestionForm()
    if form.validate_on_submit():
        question_data = {
            'text': form.question_text.data,
            'correct_answer': form.correct_answer.data,
            'image': form.image.data
        }

        if 'questions_data' not in session:
            session['questions_data'] = []

        session['questions_data'].append(question_data)
        session.modified = True
        # TODO: fix
        if question_data['image']:
            try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f'''{session['test_title']}{q_num}.png'''))
            except FileNotFoundError:
                pass
            filename = secure_filename(question_data['image'].filename)
            question_data['image'].save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            os.rename(os.path.join(app.config['UPLOAD_FOLDER'], filename),
                  os.path.join(app.config['UPLOAD_FOLDER'], f'''{session['test_title']}{q_num}.png'''))

            question_data['image'] = f'''{session['test_title']}{q_num}.png'''
        else:
            question_data['image'] = 'NO'

        if q_num < session['num_questions']:
            print(session)
            return redirect(url_for('add_questions', q_num=q_num + 1))
        else:

            print(session)
            new_test = Test(
                title=session['test_title'],
                created_by=current_user.id,
                class_id=session.get('class_id')
            )
            db.session.add(new_test)
            db.session.commit()

            for q_data in session['questions_data']:

                question = Question(
                    text=q_data['text'],
                    correct_answer=q_data['correct_answer'],
                    img = q_data['image'],
                    test_id=new_test.id
                )
                db.session.add(question)
                db.session.commit()

            db.session.commit()

            session.pop('test_title', None)
            session.pop('num_questions', None)
            session.pop('class_id', None)
            session.pop('questions_data', None)

            flash('Тест успешно создан!', 'success')
            return redirect(url_for('teacher_dashboard'))

    return render_template('add_questions.html', form=form, q_num=q_num,
                           total=session.get('num_questions', 0))


@app.route('/take_test/<int:test_id>', methods=['GET', 'POST'])
@login_required
def take_test(test_id):
    if current_user.role != 'student':
        return redirect(url_for('teacher_dashboard'))

    test = Test.query.get_or_404(test_id)
    questions = test.questions

    if request.method == 'POST':
        score = 0
        total_points = 0

        result = TestResult(
            student_id=current_user.id,
            test_id=test_id,
            score=0,
            grade=0
        )
        db.session.add(result)
        db.session.commit()

        for question in questions:
            answer_key = f'question_{question.id}'
            if answer_key in request.form:
                user_answer = request.form[answer_key]

                is_correct = (user_answer.lower().strip() == question.correct_answer.lower().strip())

                if is_correct:
                    score += question.points
                    print(f"Вопрос {question.id}: ПРАВИЛЬНО! {user_answer} == {question.correct_answer}")
                else:
                    print(f"Вопрос {question.id}: НЕПРАВИЛЬНО! {user_answer} != {question.correct_answer}")

                total_points += question.points

                student_answer = StudentAnswer(
                    result_id=result.id,
                    question_id=question.id,
                    answer=user_answer,
                    is_correct=is_correct
                )
                db.session.add(student_answer)
            else:
                print(f"Вопрос {question.id}: ОТВЕТ НЕ НАЙДЕН!")
                student_answer = StudentAnswer(
                    result_id=result.id,
                    question_id=question.id,
                    answer="[Нет ответа]",
                    is_correct=False
                )
                db.session.add(student_answer)

        db.session.commit()

        if total_points > 0:
            percentage = (score / total_points * 100)
        else:
            percentage = 0

        grade = calculate_grade(percentage)

        result.score = percentage
        result.grade = grade
        db.session.commit()

        print(f"ИТОГ: {score} из {total_points} баллов = {percentage}%, оценка {grade}")

        correct_answers_count = StudentAnswer.query.filter_by(
            result_id=result.id,
            is_correct=True
        ).count()

        current_user.level += correct_answers_count // 10
        db.session.commit()

        return redirect(url_for('test_result', result_id=result.id))

    return render_template('take_test.html', test=test, questions=questions)


@app.route('/test_result/<int:result_id>')
@login_required
def test_result(result_id):
    result = TestResult.query.get_or_404(result_id)

    if result.student_id != current_user.id and current_user.role != 'teacher':
        flash('У вас нет доступа к этому результату', 'danger')
        return redirect(url_for('student_dashboard'))

    return render_template('test_result.html', result=result)


@app.route('/student_results')
@login_required
def student_results():
    if current_user.role != 'teacher':
        return redirect(url_for('student_dashboard'))

    students = User.query.filter_by(role='student').all()
    results_data = []

    for student in students:
        student_tests = TestResult.query.filter_by(student_id=student.id).all()
        for test_result in student_tests:
            wrong_answers = StudentAnswer.query.filter_by(
                result_id=test_result.id,
                is_correct=False
            ).all()

            results_data.append({
                'student': student,
                'test': test_result.test,
                'score': test_result.score,
                'grade': test_result.grade,
                'completed_at': test_result.completed_at,
                'wrong_questions': wrong_answers
            })

    return render_template('student_results.html', results=results_data)

@app.route('/create_class', methods=['GET', 'POST'])
@login_required
def create_class():
    if current_user.role != 'teacher':
        return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        level = int(request.form['class_level'])
        letter = request.form['class_letter']

        existing_class = Class.query.filter_by(level=level, letter=letter, teacher_id=current_user.id).first()
        if existing_class:
            flash('Такой класс уже существует', 'danger')
        else:
            new_class = Class(level=level, letter=letter, teacher_id=current_user.id)
            db.session.add(new_class)
            db.session.commit()
            flash(f'Класс {level}{letter} успешно создан!', 'success')

        return redirect(url_for('teacher_dashboard'))

    return render_template('create_class.html')


@app.route('/class_statistics/<int:class_id>')
@login_required
def class_statistics(class_id):
    if current_user.role != 'teacher':
        return redirect(url_for('student_dashboard'))

    class_obj = Class.query.get_or_404(class_id)

    if class_obj.teacher_id != current_user.id:
        flash('У вас нет доступа к этому классу', 'danger')
        return redirect(url_for('teacher_dashboard'))

    students = User.query.filter_by(role='student', class_level=class_obj.level, class_letter=class_obj.letter).all()

    tests = Test.query.filter_by(class_id=class_id).all()

    chart_data = {
        'students': [],
        'avg_scores': [],
        'tests': []
    }

    for student in students:
        student_results = TestResult.query.filter_by(student_id=student.id).all()
        avg_score = sum(r.score for r in student_results) / len(student_results) if student_results else 0
        chart_data['students'].append(student.username)
        chart_data['avg_scores'].append(round(avg_score, 2))

    for test in tests:
        test_results = TestResult.query.filter(TestResult.test_id == test.id).filter(
            TestResult.student_id.in_([s.id for s in students])).all()
        avg_score = sum(r.score for r in test_results) / len(test_results) if test_results else 0
        chart_data['tests'].append({
            'title': test.title,
            'avg_score': round(avg_score, 2)
        })

    return render_template('class_statistics.html', class_obj=class_obj, students=students, tests=tests,
                           chart_data=chart_data)


@app.route('/my_classes')
@login_required
def my_classes():
    if current_user.role != 'teacher':
        return redirect(url_for('student_dashboard'))

    classes = Class.query.filter_by(teacher_id=current_user.id).all()

    return render_template('my_classes.html', classes=classes)


@app.route('/teacher_results')
@login_required
def teacher_results():
    if current_user.role != 'teacher':
        return redirect(url_for('student_dashboard'))

    classes = Class.query.filter_by(teacher_id=current_user.id).all()

    results_data = []

    for class_obj in classes:
        students = User.query.filter_by(
            role='student',
            class_level=class_obj.level,
            class_letter=class_obj.letter
        ).all()

        for student in students:
            test_results = TestResult.query.filter_by(student_id=student.id).all()

            for result in test_results:
                wrong_answers = StudentAnswer.query.filter_by(
                    result_id=result.id,
                    is_correct=False
                ).all()

                results_data.append({
                    'class_name': class_obj.name,
                    'student': student,
                    'test': result.test,
                    'score': result.score,
                    'grade': result.grade,
                    'completed_at': result.completed_at,
                    'wrong_answers': wrong_answers
                })

    return render_template('teacher_results.html', results=results_data, classes=classes)


@app.route('/create_test', methods=['GET', 'POST'])
@login_required
def create_test():
    if current_user.role != 'teacher':
        return redirect(url_for('student_dashboard'))

    teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()

    if not teacher_classes:
        flash('Сначала создайте класс в разделе "Создать класс"', 'warning')
        return redirect(url_for('teacher_dashboard'))

    form = CreateTestForm(teacher_id=current_user.id)

    if form.validate_on_submit():
        session['test_title'] = form.test_title.data
        session['num_questions'] = form.num_questions.data
        session['class_id'] = form.class_id.data
        session['questions_data'] = []
        return redirect(url_for('add_questions', q_num=1))

    return render_template('create_test.html', form=form, classes=teacher_classes)


if __name__ == '__main__':
    app.run(debug=True)