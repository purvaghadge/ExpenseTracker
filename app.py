import os
import json
from flask import Flask, render_template, request, redirect, session, url_for
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

import pyrebase

app = Flask(__name__)
app.secret_key = "supersecretkey"  # required for session

# =========================
# FIREBASE ADMIN (DB)
# =========================

firebase_key = json.loads(os.environ.get("FIREBASE_KEY"))
cred = credentials.Certificate(firebase_key)
firebase_admin.initialize_app(cred)

db = firestore.client()

# =========================
# FIREBASE AUTH (LOGIN)
# =========================

firebase_config = {
    "apiKey": "YOUR_API_KEY",
    "authDomain": "YOUR_PROJECT.firebaseapp.com",
    "databaseURL": "",
    "projectId": "YOUR_PROJECT_ID",
    "storageBucket": "YOUR_PROJECT.appspot.com",
    "messagingSenderId": "",
    "appId": ""
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

# =========================
# LOGIN PAGE
# =========================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            user = auth.sign_in_with_email_and_password(email, password)

            session['user'] = user['localId']
            session['email'] = email

            return redirect('/')

        except:
            return "Invalid credentials"

    return render_template('login.html')

# =========================
# SIGNUP PAGE
# =========================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            user = auth.create_user_with_email_and_password(email, password)

            session['user'] = user['localId']
            session['email'] = email

            return redirect('/')

        except:
            return "Signup failed"

    return render_template('signup.html')

# =========================
# LOGOUT
# =========================

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# =========================
# HOME PAGE (PROTECTED)
# =========================

@app.route('/')
def index():

    if 'user' not in session:
        return redirect('/login')

    uid = session['user']

    expenses_ref = db.collection('expenses').where('uid', '==', uid)
    docs = expenses_ref.stream()

    expenses = []
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

        expense_date = datetime.strptime(data['date'], "%d-%m-%Y")

        month_name = expense_date.strftime("%B")
        year = expense_date.year
        month_key = f"{month_name} {year}"

        if month_key not in monthly_data:
            monthly_data[month_key] = {"expenses": [], "total": 0}

        monthly_data[month_key]["expenses"].append(data)
        monthly_data[month_key]["total"] += amount

        if expense_date.month == current_month and expense_date.year == current_year:
            monthly_total += amount

        if expense_date.year == current_year:
            yearly_total += amount

        category = data['category']
        category_totals[category] = category_totals.get(category, 0) + amount

        expenses.append(data)

    return render_template(
        'index.html',
        expenses=expenses,
        total=round(total, 2),
        monthly_total=round(monthly_total, 2),
        yearly_total=round(yearly_total, 2),
        category_totals=category_totals,
        monthly_data=monthly_data,
        today=datetime.now().strftime("%d %B %Y")
    )

# =========================
# ADD EXPENSE (USER SPECIFIC)
# =========================

@app.route('/add', methods=['POST'])
def add_expense():

    if 'user' not in session:
        return redirect('/login')

    uid = session['user']

    db.collection('expenses').add({
        'title': request.form['title'],
        'amount': request.form['amount'],
        'category': request.form['category'],
        'date': datetime.now().strftime("%d-%m-%Y"),
        'uid': uid
    })

    return redirect('/')

# =========================
# DELETE EXPENSE
# =========================

@app.route('/delete/<id>')
def delete_expense(id):

    db.collection('expenses').document(id).delete()

    return redirect('/')