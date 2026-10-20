from sqlalchemy import inspect, text

from app.database import engine

inspector = inspect(engine)
columns = {
    column["name"]
    for column in inspector.get_columns("conversations")
}

if "user_id" not in columns:
    with engine.begin() as connection:
        connection.execute(
            text("""
                ALTER TABLE conversations
                ADD COLUMN user_id INTEGER
                REFERENCES users(id) ON DELETE SET NULL
            """)
        )
        connection.execute(
            text("""
                CREATE INDEX ix_conversations_user_id
                ON conversations(user_id)
            """)
        )
    print("Migration completed: user_id added.")
else:
    print("Migration skipped: user_id already exists.")