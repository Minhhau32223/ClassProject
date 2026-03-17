import MySQLdb

try:
    db = MySQLdb.connect(host="localhost", user="root", passwd="123456")
    cursor = db.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS dacn_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    print("Database dacn_db created or already exists!")
    db.close()
except Exception as e:
    print("Error creating database:", e)
