import mysql.connector
import streamlit as st

def get_connection():
    return mysql.connector.connect(
        host="gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com", # Get this from TiDB Cloud 'Connect' button
        port=4000,
        user="RiYXRxY9XtkdffG.root",
        password="nj3WgTfjafiFMEj1",
        database="SalesHub_TiDB",
        ssl_verify_cert=False # TiDB Cloud requires SSL
    )

def run_query(query, params=None):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if query.strip().upper().startswith("SELECT"):
            result = cursor.fetchall()
        else:
            conn.commit()
            result = None
        conn.close()
        return result
    except Exception as e:
        st.error(f"Database Error: {e}")
        return None