from main import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():

    teacher = User(
        username="teacher",
        password=generate_password_hash("teacher123"),
        role="teacher",
        level=1,
        teacher_code="ADMIN123"
    )


    student = User(
        username="student",
        password=generate_password_hash("student123"),
        role="student",
        level=1,
        class_level=10,
        class_letter="А"
    )


    db.session.add(teacher)
    db.session.add(student)
    db.session.commit()

    print("   Созданы тестовые пользователи:")
    print("   Учитель: teacher / teacher123")
    print("   Ученик: student / student123")


    users = User.query.all()
    print(f"\nВсего пользователей в базе: {len(users)}")
    for u in users:
        print(f"  - {u.username} ({u.role})")