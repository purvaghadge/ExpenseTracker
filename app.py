import os
import json
from flask import Flask, render_template, request, redirect, session
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

# ================= FIREBASE =================

firebase_key = os.environ.get("FIREBASE_KEY")

if not firebase_key:
    raise Exception("FIREBASE_KEY not set in environment variables")

cred = credentials.Certificate(json.loads(firebase_key))

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ================= HOME =================

@app.route('/')
def index():

    if 'user' not in session:
        return redirect('/login')

    uid = session['user']

    expenses_ref = db.collection('expenses').where('uid', '==', uid)
    docs = expenses_ref.stream()

    total = 0
    monthly_total = 0
    yearly_total = 0

    category_totals = {}
    monthly_data = {}

    current_month = datetime.now().month
    current_year = datetime.now().year

    for doc in docs:

        data = doc.to_dict()
        data['id'] = doc.id

        amount = float(data['amount'])

        total += amount

        expense_date = datetime.strptime(
            data['date'],
            "%d-%m-%Y"
        )

        month_key = expense_date.strftime("%Y-%m")
        month_label = expense_date.strftime("%B %Y")

        if month_key not in monthly_data:

            monthly_data[month_key] = {
                "label": month_label,
                "expenses": [],
                "total": 0
            }

        monthly_data[month_key]["expenses"].append(data)
        monthly_data[month_key]["total"] += amount

        if expense_date.month == current_month and expense_date.year == current_year:
            monthly_total += amount

        if expense_date.year == current_year:
            yearly_total += amount

        category = data['category']

        category_totals[category] = (
            category_totals.get(category, 0) + amount
        )

    monthly_data = dict(
        sorted(monthly_data.items(), reverse=True)
    )

    return render_template(
        'index.html',
        total=round(total, 2),
        monthly_total=round(monthly_total, 2),
        yearly_total=round(yearly_total, 2),
        category_totals=category_totals,
        monthly_data=monthly_data,
        today=datetime.now().strftime("%d %B %Y"),
        email=session.get('email')
    )

# ================= ADD =================

@app.route('/add', methods=['POST'])
def add_expense():

    if 'user' not in session:
        return redirect('/login')

    uid = session['user']

    db.collection('expenses').add({
        'title': request.form['title'],
        'amount': float(request.form['amount']),
        'category': request.form['category'],
        'date': datetime.now().strftime("%d-%m-%Y"),
        'uid': uid
    })

    return redirect('/')

# ================= DELETE =================

@app.route('/delete/<id>')
def delete_expense(id):

    if 'user' not in session:
        return redirect('/login')

    doc = db.collection('expenses').document(id).get()

    if doc.exists and doc.to_dict().get('uid') == session['user']:
        db.collection('expenses').document(id).delete()

    return redirect('/')

# ================= LOGOUT =================

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')

# ================= LOGIN =================

@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        users = db.collection('users') \
            .where('email', '==', email) \
            .stream()

        user_found = None

        for user in users:
            user_found = user.to_dict()

        if user_found:

            stored_password = user_found['password']

            if check_password_hash(stored_password, password):

                session['user'] = user_found['uid']
                session['email'] = user_found['email']

                return redirect('/')

            else:
                error = "Invalid Password"

        else:
            error = "User not found"

    return render_template(
        "login.html",
        error=error
    )

# ================= SIGNUP =================

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    error = None

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        existing_users = db.collection('users') \
            .where('email', '==', email) \
            .stream()

        user_exists = False

        for user in existing_users:
            user_exists = True

        if user_exists:

            error = "Email already registered"

            return render_template(
                'signup.html',
                error=error
            )

        uid = email.replace("@", "_").replace(".", "_")

        db.collection('users').document(uid).set({

            'email': email,

            'password': generate_password_hash(password),

            'uid': uid

        })

        session['user'] = uid
        session['email'] = email

        return redirect('/')

    return render_template(
        'signup.html',
        error=error
    )

# ================= MAIN =================

if __name__ == '__main__':
    app.run(debug=True)