from flask import Flask, render_template, redirect, url_for, flash, session, request
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email
import bcrypt
from flask_mysqldb import MySQL
from flask import jsonify
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretkey123'


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login to access the system.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'system123'
app.config['MYSQL_DB'] = 'library_db'

mysql = MySQL(app)


# --- WTFORMS CLASSES (As required by your HTML files) ---
class LoginForm(FlaskForm):
    email = StringField('Email address:', validators=[DataRequired(), Email()])
    password = PasswordField('Password:', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username:', validators=[DataRequired()])
    email = StringField('Email address:', validators=[DataRequired(), Email()])
    password = PasswordField('Password:', validators=[DataRequired()])
    submit = SubmitField('Register')


# --- CENTRAL DASHBOARD ---
@app.route('/')
@login_required
def dashboard():
    return render_template('index.html')


# --- USER REGISTRATION ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data.encode('utf-8')
        
        # पासवर्ड एन्क्रिप्शन
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

        cursor = mysql.connection.cursor()
        
        # चेक करें कि ईमेल पहले से तो नहीं है
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            flash("Email already registered! Please login.")
            cursor.close()
            return redirect(url_for('register'))

        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, hashed_password)
        )
        mysql.connection.commit()
        cursor.close()
        flash("Registration successful! Please login.")
        return redirect(url_for('login'))
        
    return render_template('register.html', form=form)

# --- API: GET STUDENT SUGGESTIONS & INFO ---
@app.route('/api/students')
@login_required
def get_students_api():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT student_id, name, phone FROM students")
    rows = cursor.fetchall()
    cursor.close()
    # लिस्ट को JSON फॉर्मेट में भेजेंगे
    student_list = [{"id": r[0], "name": r[1], "phone": r[2]} for r in rows]
    return jsonify(student_list)

# --- API: GET BOOK SUGGESTIONS & INFO ---
@app.route('/api/books')
@login_required
def get_books_api():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, title FROM books WHERE quantity > 0")
    rows = cursor.fetchall()
    cursor.close()
    book_list = [{"id": str(r[0]), "title": r[1]} for r in rows]
    return jsonify(book_list)


# --- USER LOGIN ---
# --- USER LOGIN (Updated for Safety) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data.encode('utf-8')

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, username, email, password FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            # 1. डेटाबेस से मिले पासवर्ड को साफ करें (strip)
            stored_hash = user[3].strip() 
            
            # 2. सुरक्षित तरीके से चेक करें
            try:
                if bcrypt.checkpw(password, stored_hash.encode('utf-8')):
                    session['user_id'] = user[0]
                    session['username'] = user[1]
                    flash("Logged in successfully!")
                    return redirect(url_for('dashboard'))
                else:
                    flash("Invalid email or password.")
            except ValueError as e:
                print(f"Bcrypt Error: {e}") # यह टर्मिनल में दिखेगा
                flash("Login failed due to data error. Please re-register.")
        else:
            flash("Invalid email or password.")
            return redirect(url_for('login'))

    return render_template('login.html', form=form)


# # --- USER LOGOUT ---
# @app.route('/logout')
# @login_required
# def logout():
#     session.clear()
#     flash("You have been logged out.")
#     return redirect(url_for('login'))


@app.route('/logout')
def logout(): # @login_required अभी के लिए हटाकर देखें
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('login'))

# --- ACTION 1: ADD NEW BOOKS ---
@app.route('/books/add', methods=['GET', 'POST'])
@login_required
def add_book():
    if request.method == 'POST':
        books_image = request.form['books_image']
        title = request.form['title']
        author = request.form['author']
        published_year = request.form['published_year']
        price = request.form['price']
        quantity = request.form['quantity']

        cursor = mysql.connection.cursor()
        cursor.execute(
            """
            INSERT INTO books (books_image, title, author, published_year, price, quantity)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (books_image, title, author, published_year, price, quantity)
        )
        mysql.connection.commit()
        cursor.close()
        
        flash("Book added successfully!")
        return redirect(url_for('view_catalog')) 
        
    return render_template('Books.html')


# --- ACTION 2: VIEW INVENTORY CATALOG ---
@app.route('/books/catalog')
@login_required
def view_catalog():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT b.id, b.books_image, b.title, b.author, b.published_year, b.price, b.quantity,
               (b.quantity - COALESCE(i.issued_count, 0)) AS available_inventory
        FROM books b
        LEFT JOIN (
            SELECT book_title, COUNT(*) AS issued_count 
            FROM issue_books 
            WHERE status = 'Issued' 
            GROUP BY book_title
        ) i ON b.title = i.book_title
    """)
    books_data = cursor.fetchall()
    cursor.close()
    return render_template('view.html', books=books_data)


# --- ACTION 3: REMOVE BOOK FROM CATALOG ---
@app.route('/books/delete/<int:id>')
@login_required
def delete_book(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM books WHERE id = %s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash("Book removed from catalog!")
    return redirect(url_for('view_catalog'))


# --- ACTION 4: ISSUE A BOOK (FORM ENTRY) ---
@app.route('/books/issue', methods=['GET', 'POST'])
@login_required
def issue_book():
    cursor = mysql.connection.cursor()
    
    if request.method == 'POST':
        student_id = request.form['student_id']
        student_name = request.form['student_name']
        student_phone = request.form['student_phone'] # नया फील्ड रिसीव किया
        book_title = request.form['book_title']
        issue_date = request.form['issue_date']
        due_date = request.form['due_date']

        # Validations
        cursor.execute("SELECT * FROM books WHERE title = %s", (book_title,))
        book = cursor.fetchone()
        if not book:
            flash("Error: Book title not found in catalog.")
            cursor.close()
            return redirect(url_for('issue_book'))

        cursor.execute("SELECT COUNT(*) FROM issue_books WHERE book_title = %s AND status = 'Issued'", (book_title,))
        current_issued = cursor.fetchone()[0]
        if current_issued >= book[6]: 
            flash("Error: No physical copies available! All units are currently Issued.")
            cursor.close()
            return redirect(url_for('issue_book'))

        cursor.execute(
            """
            INSERT INTO issue_books (student_id, student_name, book_title, issue_date, due_date, status)
            VALUES (%s, %s, %s, %s, %s, 'Issued')
            """,
            (student_id, student_name, book_title, issue_date, due_date)
        )
        mysql.connection.commit()
        cursor.close()
        flash("Book successfully Issued!")
        return redirect(url_for('view_issued_books'))

    prefilled_title = ""
    book_id = request.args.get('book_id')
    if book_id:
        cursor.execute("SELECT title FROM books WHERE id = %s", (book_id,))
        res = cursor.fetchone()
        if res: prefilled_title = res[0]
            
    cursor.close()
    return render_template('issued_books.html', prefilled_title=prefilled_title)


# --- ACTION 5: VIEW ISSUED BOOKS LIST ---
@app.route('/books/issued-list')
@login_required
def view_issued_books():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT id, student_id, student_name, book_title, 
               issue_date, due_date, return_date, status 
        FROM issue_books
    """)
    loans_data = cursor.fetchall()
    cursor.close()
    return render_template('issue_book.html', loans=loans_data)

# --- ACTION: REGISTER NEW STUDENT (WITH AUTO ID) ---# --- ACTION: REGISTER NEW STUDENT (WITH AUTO ID & PHONE VALIDATION) ---
@app.route('/students/register', methods=['GET', 'POST'])
@login_required
def register_student():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone'].strip() # स्पेस हटाने के लिए
        address = request.form['address']

        # 🛠️ फोन नंबर की लंबाई जांचने का लॉजिक (Must be at least 10 digits)
        if len(phone) < 10:
            flash("Error: Phone number must be at least 10 digits long!")
            return render_template('register_student.html')

        cursor = mysql.connection.cursor()
        
        # Auto-ID Generation Logic
        cursor.execute("SELECT COUNT(*) FROM students")
        count = cursor.fetchone()[0]
        next_id_number = 1001 + count
        student_id = f"STU{next_id_number}"

        cursor.execute(
            """
            INSERT INTO students (student_id, name, phone, address)
            VALUES (%s, %s, %s, %s)
            """,
            (student_id, name, phone, address)
        )
        mysql.connection.commit()
        cursor.close()

        flash(f"Student Registered Successfully! Generated ID: {student_id}")
        return redirect(url_for('view_students'))

    return render_template('register_student.html')


# --- ACTION: VIEW REGISTERED STUDENTS LIST ---
@app.route('/students/list')
@login_required
def view_students():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT student_id, name, phone, address FROM students ORDER BY created_at DESC")
    students_data = cursor.fetchall()
    cursor.close()
    return render_template('view_students.html', students=students_data)


# --- ACTION 6: RETURN AN ISSUED BOOK ---
@app.route('/books/return/<int:id>')
@login_required
def return_book(id):
    cursor = mysql.connection.cursor()
    cursor.execute(
        """
        UPDATE issue_books
        SET status = 'Returned', return_date = CURDATE()
        WHERE id = %s
        """,
        (id,)
    )
    mysql.connection.commit()
    cursor.close()
    flash("Book return processed successfully! Status updated to Returned ✅")
    return redirect(url_for('view_issued_books'))


if __name__ == '__main__':
    app.run(debug=True)