import oracledb

try:
    connection = oracledb.connect(
        user="system",
        password="suresh",
        dsn="127.0.0.1:1521/XE"
    )

    print("Connected Successfully!")

except Exception as e:
    print("Connection Failed:", e)