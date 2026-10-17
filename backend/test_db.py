
def main():
    from sqlalchemy import text
    from database import engine

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT DATABASE()"))
            database_name = result.scalar()

            print("Connection successful!")
            print("Connected database:", database_name)

    except Exception as error:
        print("Database connection failed.")
        print("Error:", error)


if __name__ == "__main__":
    main()
