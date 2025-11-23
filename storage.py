import mysql.connector
from mysql.connector import Error
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
import sys

def get_connection():
    """Creates and returns a connection to the MySQL database."""
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def init_db() -> None:
    """Initializes the database tables if they do not exist."""
    # First, try to connect without database to create it if needed
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
            cursor.close()
            conn.close()
    except Error as e:
        print(f"Error creating database: {e}")
        return

    conn = get_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        
        # Subjects Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                exam_date DATE NOT NULL
            )
        """)

        # Topics Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                subject_id INT,
                name VARCHAR(255) NOT NULL,
                type VARCHAR(50),
                difficulty VARCHAR(50),
                status VARCHAR(50) DEFAULT 'pending',
                assigned_date DATE,
                repetition_count INT DEFAULT 0,
                ease_factor FLOAT DEFAULT 2.5,
                `interval` INT DEFAULT 0,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
    except Error as e:
        print(f"Error initializing tables: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def add_subject(name: str, exam_date: str) -> int:
    """Adds a new subject and returns its ID."""
    conn = get_connection()
    if conn is None: return -1
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO subjects (name, exam_date) VALUES (%s, %s)", (name, exam_date))
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        print(f"Error adding subject: {e}")
        return -1
    finally:
        cursor.close()
        conn.close()

def add_topic(subject_id: int, name: str, type: str, difficulty: str, assigned_date: str, 
              repetition_count: int = 0, ease_factor: float = 2.5, interval: int = 0) -> None:
    """Adds a new topic to a subject."""
    conn = get_connection()
    if conn is None: return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO topics (subject_id, name, type, difficulty, assigned_date, status, repetition_count, ease_factor, `interval`)
            VALUES (%s, %s, %s, %s, %s, 'pending', %s, %s, %s)
        """, (subject_id, name, type, difficulty, assigned_date, repetition_count, ease_factor, interval))
        conn.commit()
    except Error as e:
        print(f"Error adding topic: {e}")
    finally:
        cursor.close()
        conn.close()

def get_topic(topic_id: int) -> dict:
    """Returns a single topic by ID."""
    conn = get_connection()
    if conn is None: return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM topics WHERE id = %s", (topic_id,))
        row = cursor.fetchone()
        if row:
            row['assigned_date'] = str(row['assigned_date'])
        return row
    except Error as e:
        print(f"Error fetching topic: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_subjects() -> list:
    """Returns a list of all subjects."""
    conn = get_connection()
    if conn is None: return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM subjects")
        return cursor.fetchall()
    except Error as e:
        print(f"Error fetching subjects: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_subject_schedule(subject_id: int) -> list:
    """Returns the schedule for a specific subject."""
    conn = get_connection()
    if conn is None: return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM topics 
            WHERE subject_id = %s 
            ORDER BY assigned_date
        """, (subject_id,))
        # Rename 'name' to 'topic' to match old schema for compatibility if needed, 
        # or better, update consumers. Let's map it here for now to minimize friction.
        rows = cursor.fetchall()
        for row in rows:
            row['topic'] = row['name']
            row['assigned_date'] = str(row['assigned_date'])
        return rows
    except Error as e:
        print(f"Error fetching schedule: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_todays_tasks() -> list:
    """Returns tasks assigned for today or overdue pending tasks."""
    conn = get_connection()
    if conn is None: return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT t.*, s.name as subject_name 
            FROM topics t
            JOIN subjects s ON t.subject_id = s.id
            WHERE t.assigned_date <= CURDATE() AND t.status = 'pending'
        """)
        rows = cursor.fetchall()
        for row in rows:
            row['topic'] = row['name']
            row['subject'] = row['subject_name']
            row['assigned_date'] = str(row['assigned_date'])
        return rows
    except Error as e:
        print(f"Error fetching today's tasks: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def update_topic_status(topic_id: int, status: str) -> None:
    """Updates the status of a topic."""
    conn = get_connection()
    if conn is None: return
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE topics SET status = %s WHERE id = %s", (status, topic_id))
        conn.commit()
    except Error as e:
        print(f"Error updating status: {e}")
    finally:
        cursor.close()
        conn.close()

def update_topic_review_data(topic_id: int, repetition_count: int, ease_factor: float, interval: int, next_date: str) -> None:
    """Updates SM-2 data and next review date."""
    conn = get_connection()
    if conn is None: return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE topics 
            SET repetition_count = %s, ease_factor = %s, `interval` = %s, assigned_date = %s, status = 'pending'
            WHERE id = %s
        """, (repetition_count, ease_factor, interval, next_date, topic_id))
        conn.commit()
    except Error as e:
        print(f"Error updating review data: {e}")
    finally:
        cursor.close()
        conn.close()
