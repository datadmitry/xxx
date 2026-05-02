from main import app, db
from models import User

with app.app_context():

    from sqlalchemy import inspect

    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print("Существующие таблицы:", tables)


    users = User.query.all()
    print(f"Количество пользователей в базе: {len(users)}")

    for user in users:
        print(f"  - {user.username} ({user.role})")