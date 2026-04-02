import MySQLdb
try:
    db = MySQLdb.connect(host='127.0.0.1', user='root', passwd='')
    cursor = db.cursor()
    cursor.execute('CREATE DATABASE IF NOT EXISTS dacn_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;')
    print('Database created successfully!')
except Exception as e:
    print('Error:', e)
