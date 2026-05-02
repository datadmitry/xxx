from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Test, Question, TestResult, StudentAnswer, Class
from forms import RegistrationForm, LoginForm, CreateTestForm, QuestionForm, SendTestForm
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
from sqlalchemy import inspect, text
import random
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


def seed_test_bank():
    if Test.query.filter(Test.class_id.is_(None)).count() > 0:
        return

    seed_user = User.query.filter_by(username='system').first()
    if not seed_user:
        seed_user = User(
            username='system',
            password=generate_password_hash('system_seed_password'),
            role='teacher',
            level=1,
            teacher_code='SYSTEM'
        )
        db.session.add(seed_user)
        db.session.commit()

    bank = [
        {
            'title': 'Математика: базовая арифметика',
            'questions': [
                ('Сколько будет 7 + 8?', '15'),
                ('Сколько будет 12 * 3?', '36'),
                ('Сколько будет 81 / 9?', '9'),
                ('Сколько будет 25 - 14?', '11'),
                ('Сколько будет 6 * 7?', '42'),
            ],
        },
        {
            'title': 'Русский язык: проверь себя',
            'questions': [
                ('Сколько падежей в русском языке?', '6'),
                ('Какая часть речи отвечает на вопрос "что делать"?', 'глагол'),
                ('Сколько букв в русском алфавите?', '33'),
                ('Антоним к слову "горячий"', 'холодный'),
                ('Синоним к слову "красивый"', 'прекрасный'),
            ],
        },
        {
            'title': 'Окружающий мир: природа',
            'questions': [
                ('Какая планета третья от Солнца?', 'Земля'),
                ('Самый большой океан', 'Тихий'),
                ('Сколько материков на Земле?', '6'),
                ('Самое высокое животное на суше', 'жираф'),
                ('Какой газ нужен для дыхания?', 'кислород'),
            ],
        },
        {
            'title': 'История: Древний мир',
            'questions': [
                ('В какой стране были построены пирамиды Гизы?', 'Египет'),
                ('Кто основал Древний Рим (по легенде)?', 'Ромул'),
                ('Какой материал использовали для письма в Древнем Египте?', 'папирус'),
                ('Бог-громовержец у древних греков', 'Зевс'),
                ('Главная река Древнего Египта', 'Нил'),
            ],
        },
        {
            'title': 'Английский язык: начальный уровень',
            'questions': [
                ('Перевод слова "cat"', 'кот'),
                ('Перевод слова "house"', 'дом'),
                ('Как по-английски "красный"?', 'red'),
                ('Как по-английски "книга"?', 'book'),
                ('Множественное число от "child"', 'children'),
            ],
        },
    ]

    for t in bank:
        test = Test(title=t['title'], created_by=seed_user.id, class_id=None)
        db.session.add(test)
        db.session.flush()
        for text, answer in t['questions']:
            db.session.add(Question(
                text=text,
                correct_answer=answer,
                img='NO',
                test_id=test.id,
            ))
    db.session.commit()


def ensure_schema():
    """Lightweight migration: add new columns if missing (SQLite)."""
    inspector = inspect(db.engine)

    user_cols = {c['name'] for c in inspector.get_columns('user')}
    with db.engine.begin() as conn:
        if 'daily_streak' not in user_cols:
            conn.execute(text('ALTER TABLE user ADD COLUMN daily_streak INTEGER DEFAULT 0'))
        if 'last_daily_date' not in user_cols:
            conn.execute(text('ALTER TABLE user ADD COLUMN last_daily_date DATE'))

    result_cols = {c['name'] for c in inspector.get_columns('test_result')}
    with db.engine.begin() as conn:
        if 'duration_seconds' not in result_cols:
            conn.execute(text('ALTER TABLE test_result ADD COLUMN duration_seconds INTEGER DEFAULT 0'))


def format_duration(total_seconds):
    if not total_seconds or total_seconds < 0:
        return '0 сек'
    total_seconds = int(total_seconds)
    minutes, seconds = divmod(total_seconds, 60)
    if minutes:
        return f'{minutes} мин {seconds} сек'
    return f'{seconds} сек'


with app.app_context():
    db.create_all()
    ensure_schema()
    seed_test_bank()


@app.context_processor
def inject_helpers():
    return {'format_duration': format_duration}


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


def _dashboard_url_for(user):
    return url_for('student_dashboard') if user.role == 'student' else url_for('teacher_dashboard')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(_dashboard_url_for(current_user))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(_dashboard_url_for(user))
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

    student_class = None
    if current_user.class_level and current_user.class_letter:
        student_class = Class.query.filter_by(
            level=current_user.class_level,
            letter=current_user.class_letter,
        ).first()

    query = (request.args.get('q') or '').strip()

    if student_class:
        base_q = Test.query.filter_by(class_id=student_class.id)
        if query:
            base_q = base_q.filter(Test.title.ilike(f'%{query}%'))
        tests = base_q.all()
    else:
        tests = []

    completed_tests = TestResult.query.filter_by(student_id=current_user.id).all()
    completed_test_ids = [result.test_id for result in completed_tests]

    today = date.today()
    daily_done_today = current_user.last_daily_date == today

    return render_template('student_dashboard.html',
                           tests=tests,
                           completed_test_ids=completed_test_ids,
                           level=current_user.level,
                           query=query,
                           streak=current_user.daily_streak or 0,
                           daily_done_today=daily_done_today)


@app.route('/teacher_dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        return redirect(url_for('student_dashboard'))

    query = (request.args.get('q') or '').strip()
    search_results = []
    if query:
        teacher_class_ids = [c.id for c in Class.query.filter_by(teacher_id=current_user.id).all()]
        search_results = Test.query.filter(
            Test.title.ilike(f'%{query}%'),
            (Test.class_id.is_(None)) |
            (Test.created_by == current_user.id) |
            (Test.class_id.in_(teacher_class_ids))
        ).all()

    return render_template('teacher_dashboard.html',
                           query=query,
                           search_results=search_results)


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
    session_key = f'test_start_{test_id}'

    if request.method == 'GET':
        session[session_key] = datetime.utcnow().isoformat()

    if request.method == 'POST':
        score = 0
        total_points = 0

        start_iso = session.pop(session_key, None)
        if start_iso:
            try:
                started_at = datetime.fromisoformat(start_iso)
                duration = max(0, int((datetime.utcnow() - started_at).total_seconds()))
            except ValueError:
                duration = 0
        else:
            duration = 0

        result = TestResult(
            student_id=current_user.id,
            test_id=test_id,
            score=0,
            grade=0,
            duration_seconds=duration,
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

    form = CreateTestForm()

    if form.validate_on_submit():
        session['test_title'] = form.test_title.data
        session['num_questions'] = form.num_questions.data
        session['class_id'] = None
        session['questions_data'] = []
        return redirect(url_for('add_questions', q_num=1))

    return render_template('create_test.html', form=form)


@app.route('/test_bank', methods=['GET', 'POST'])
@login_required
def test_bank():
    if current_user.role != 'teacher':
        return redirect(url_for('student_dashboard'))

    teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()

    if not teacher_classes:
        flash('Сначала создайте класс в разделе "Создать класс"', 'warning')
        return redirect(url_for('teacher_dashboard'))

    form = SendTestForm(teacher_id=current_user.id)

    if form.validate_on_submit():
        source_test = Test.query.get_or_404(form.test_id.data)
        target_class = Class.query.get_or_404(form.class_id.data)

        if target_class.teacher_id != current_user.id:
            flash('У вас нет доступа к этому классу', 'danger')
            return redirect(url_for('test_bank'))

        already = Test.query.filter_by(
            title=source_test.title,
            class_id=target_class.id,
            created_by=current_user.id,
        ).first()
        if already:
            flash(f'Тест "{source_test.title}" уже отправлен в класс {target_class.name}', 'warning')
            return redirect(url_for('test_bank'))

        new_test = Test(
            title=source_test.title,
            created_by=current_user.id,
            class_id=target_class.id,
        )
        db.session.add(new_test)
        db.session.flush()

        for q in source_test.questions:
            db.session.add(Question(
                text=q.text,
                correct_answer=q.correct_answer,
                img=q.img,
                points=q.points,
                test_id=new_test.id,
            ))
        db.session.commit()

        flash(f'Тест "{source_test.title}" отправлен в класс {target_class.name}', 'success')
        return redirect(url_for('test_bank'))

    bank_tests = Test.query.filter(Test.class_id.is_(None)).all()
    own_tests = Test.query.filter(
        Test.created_by == current_user.id,
        Test.class_id.isnot(None),
    ).all()

    return render_template(
        'test_bank.html',
        form=form,
        bank_tests=bank_tests,
        own_tests=own_tests,
        classes=teacher_classes,
    )


DAILY_QUIZ_POOL = [
    {'q': 'Сколько будет 13 + 27?', 'a': '40'},
    {'q': 'Сколько континентов на Земле?', 'a': '6'},
    {'q': 'Столица Франции?', 'a': 'Париж'},
    {'q': 'Самая большая планета Солнечной системы?', 'a': 'Юпитер'},
    {'q': 'Кто написал "Войну и мир"?', 'a': 'Толстой'},
    {'q': 'Химический символ воды?', 'a': 'H2O'},
    {'q': 'Сколько граней у куба?', 'a': '6'},
    {'q': 'В каком году человек впервые полетел в космос?', 'a': '1961'},
    {'q': 'Сколько будет 9 в квадрате?', 'a': '81'},
    {'q': 'Самый длинный материк?', 'a': 'Евразия'},
    {'q': 'Перевод слова "friend"', 'a': 'друг'},
    {'q': 'Сколько струн у классической гитары?', 'a': '6'},
    {'q': 'Кто написал "Евгения Онегина"?', 'a': 'Пушкин'},
    {'q': 'Сколько минут в часе?', 'a': '60'},
    {'q': 'Какая часть речи "быстро"?', 'a': 'наречие'},
]


def _daily_question_for(d):
    return DAILY_QUIZ_POOL[d.toordinal() % len(DAILY_QUIZ_POOL)]


@app.route('/daily_quiz', methods=['GET', 'POST'])
@login_required
def daily_quiz():
    if current_user.role != 'student':
        return redirect(url_for('teacher_dashboard'))

    today = date.today()
    already_done = current_user.last_daily_date == today
    question = _daily_question_for(today)

    feedback = None
    if request.method == 'POST' and not already_done:
        user_answer = (request.form.get('answer') or '').strip()
        is_correct = user_answer.lower() == question['a'].lower()
        if is_correct:
            yesterday = today - timedelta(days=1)
            if current_user.last_daily_date == yesterday:
                current_user.daily_streak = (current_user.daily_streak or 0) + 1
            else:
                current_user.daily_streak = 1
            current_user.last_daily_date = today
            db.session.commit()
            flash(f'Верно! Серия: {current_user.daily_streak} дн.', 'success')
            return redirect(url_for('daily_quiz'))
        else:
            feedback = {
                'correct': False,
                'answer': user_answer,
                'right': question['a'],
            }

    return render_template(
        'daily_quiz.html',
        question=question,
        already_done=already_done,
        streak=current_user.daily_streak or 0,
        feedback=feedback,
    )


if __name__ == '__main__':
    app.run(debug=True)