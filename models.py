from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    level = db.Column(db.Integer, default=1)
    class_level = db.Column(db.Integer, nullable=True)
    class_letter = db.Column(db.String(1), nullable=True)
    teacher_code = db.Column(db.String(50), nullable=True)

    test_results = db.relationship('TestResult', backref='student', lazy=True)


class Test(db.Model):
    __tablename__ = 'test'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=True)  # теперь необязательный

    # ПРОСТАЯ связь один-ко-многим (один тест — много вопросов)
    questions = db.relationship('Question', backref='test', lazy=True)
    results = db.relationship('TestResult', backref='test', lazy=True)


class Question(db.Model):
    __tablename__ = 'question'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(500), nullable=False)
    img = db.Column(db.Text)
    points = db.Column(db.Integer, default=1)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)  # простая связь

    student_answers = db.relationship('StudentAnswer', backref='question', lazy=True)


class TestResult(db.Model):
    __tablename__ = 'test_result'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    answers = db.relationship('StudentAnswer', backref='result', lazy=True)


class StudentAnswer(db.Model):
    __tablename__ = 'student_answer'
    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey('test_result.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)


class Class(db.Model):
    __tablename__ = 'class'
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.Integer, nullable=False)
    letter = db.Column(db.String(1), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    teacher = db.relationship('User', backref='classes')
    tests = db.relationship('Test', backref='class_ref', lazy=True)

    @property
    def name(self):
        return f"{self.level}{self.letter}"