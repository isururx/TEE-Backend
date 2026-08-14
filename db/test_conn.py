from sqlalchemy import text
from app.db.database import engine


try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))

        print("✅ Supabase PostgreSQL connected!")
        print("Result:", result.fetchone())

except Exception as e:
    print("❌ Database connection failed!")
    print(e)