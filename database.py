from flask import Flask
import mysql.connector

app = Flask(__name__)

# पहले बिना डेटाबेस नाम के कनेक्ट करेंगे ताकि अगर डेटाबेस डिलीट हो चुका हो तो एरर न आए
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="system123"
)

cursor = db.cursor()

# ---- फ्रेश स्टार्ट लॉजिक (पुरानी गड़बड़ मिटाने के लिए) ----
cursor.execute("DROP DATABASE IF EXISTS library_db")
print("Old Database Dropped Clean 🗑️")

cursor.execute("CREATE DATABASE library_db")
print("Database Created Successfully ✅")

cursor.execute("USE library_db")

# 1. USERS TABLE
cursor.execute("""
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL
)
""")
print("Users Table Created ✅")


# 2. BOOKS TABLE (अब इसमें quantity कॉलम डेटाबेस में 100% बन जाएगा)
cursor.execute("""
CREATE TABLE books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    books_image VARCHAR(255),
    title VARCHAR(200) NOT NULL,
    author VARCHAR(200) NOT NULL,
    published_year INT,
    price DECIMAL(10,2),
    quantity INT NOT NULL DEFAULT 1 
)
""")
print("Books Table Created ✅")


# 3. STUDENTS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    student_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    address TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")
print("Students Table Created ✅")


# 4. ISSUE BOOKS TABLE
cursor.execute("""
CREATE TABLE issue_books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(50) NOT NULL,  -- इसे VARCHAR किया ताकि STU101 जैसे फॉर्मेट सपोर्ट हों
    student_name VARCHAR(100) NOT NULL,
    book_title VARCHAR(255) NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    return_date DATE NULL,
    status VARCHAR(20) DEFAULT 'Issued'
)
""")
print("issue_books Table Created ✅")

# कनेक्शन सुरक्षित बंद करेंगे
cursor.close()
db.close()


@app.route('/')
def home():
    return """
    <h1>Library Management System 📚</h1>
    <p>Database Connected & Tables Rebuilt Successfully ✅</p>
    <h3>Active System Tables:</h3>
    <ul>
        <li>users</li>
        <li>books (with live quantity)</li>
        <li>students</li>
        <li>issue_books</li>
    </ul>
    """

if __name__ == "__main__":
    app.run(debug=True)