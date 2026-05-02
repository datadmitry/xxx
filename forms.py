from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, IntegerField, FileField
from flask_wtf.file import FileAllowed, FileRequired
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Optional
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, NumberRange
from models import User


class RegistrationForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(min=3, max=100)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Роль', choices=[('student', 'Ученик'), ('teacher', 'Учитель')], validators=[DataRequired()])

    # Поля для ученика
    class_level = SelectField('Номер класса',
                              choices=[('', 'Выберите номер')] + [(str(i), str(i)) for i in range(1, 12)])
    class_letter = SelectField('Буква класса',
                               choices=[('', 'Выберите букву'), ('А', 'А'), ('Б', 'Б'), ('В', 'В'), ('Г', 'Г'),
                                        ('Д', 'Д'), ('Е', 'Е')])

    # Поле для учителя
    teacher_code = StringField('Код учителя')

    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Это имя пользователя уже занято. Пожалуйста, выберите другое.')


class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = SubmitField('Запомнить меня')
    submit = SubmitField('Войти')


class QuestionForm(FlaskForm):
    question_text = TextAreaField('Вопрос', validators=[DataRequired()])
    image = FileField('Вставьте изображение', default=False, validators=[FileAllowed(['jpg', 'png', 'jpeg']),
                                                                         Optional()])
    correct_answer = StringField('Правильный ответ', validators=[DataRequired()])
    submit = SubmitField('Далее')  # Добавлено поле submit


class CreateTestForm(FlaskForm):
    test_title = StringField('Название теста', validators=[DataRequired()])
    num_questions = IntegerField('Количество вопросов', validators=[DataRequired(), NumberRange(min=1, max=50)])
    submit = SubmitField('Далее')


class SendTestForm(FlaskForm):
    test_id = SelectField('Тест', coerce=int, validators=[DataRequired()])
    class_id = SelectField('Класс', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Отправить ученикам')

    def __init__(self, teacher_id, *args, **kwargs):
        super(SendTestForm, self).__init__(*args, **kwargs)
        from models import Class, Test
        classes = Class.query.filter_by(teacher_id=teacher_id).all()
        self.class_id.choices = [(c.id, c.name) for c in classes]
        bank_tests = Test.query.filter(
            (Test.class_id.is_(None)) | (Test.created_by == teacher_id)
        ).all()
        self.test_id.choices = [(t.id, t.title) for t in bank_tests]