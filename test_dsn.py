import psycopg2

# Явная DSN-строка
dsn = "host=localhost port=5432 user=student password=student_secure_password dbname=wp_labs"
print("DSN:", repr(dsn))
try:
    conn = psycopg2.connect(dsn)
    print("Connection OK")
    cur = conn.cursor()
    cur.execute("SELECT 1")
    print("Result:", cur.fetchone())
    cur.close()
    conn.close()
except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()