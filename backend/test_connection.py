from database.connection import test_connection

try:
    result = test_connection()
    print("Database connection successful!")
    print("Database:", result[0])
    print("User:", result[1])
    print("PostgreSQL version:", result[2])
except Exception as error:
    print("Database connection failed.")
    print(type(error).__name__ + ":", error)
