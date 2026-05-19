import os
import json
from flask import Flask, render_template, request, redirect, session, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret")

firebase_key = json.loads(os.environ.get("FIREBASE_KEY"))
cred = credentials.Certificate(firebase_key)
firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------- HOME (DASHBOARD) ----------------
@app.route('/')
def index():
    if 'user' not in session:
        return redirect('/login')

    uid = session['user']

    docs = db.collection('expenses').where('uid', '==', uid).stream()

    yearly_data = {}
    total = 0

    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id

        amount = float(d['amount'])
        total += amount

        date = datetime.strptime(d['date'], "%d-%m-%Y")
        year = str(date.year)
        month = date.strftime("%B")

        yearly_data.setdefault(year, {})
        yearly_data[year].setdefault(month, {"expenses": [], "total": 0})

        yearly_data[year][month]["expenses"].append(d)
        yearly_data[year][month]["total"] += amount

    return render_template("dashboard.html",
        yearly_data=yearly_data,
        total=round(total, 2),
        email=session.get('email')
    )

# ---------------- ADD ----------------
@app.route('/add', methods=['POST'])
def add_expense():
    if 'user' not in session:
        return jsonify({"status": "error"})

    uid = session['user']

    db.collection('expenses').add({
        "title": request.form['title'],
        "amount": request.form['amount'],
        "category": request.form['category'],
        "date": datetime.now().strftime("%d-%m-%Y"),
        "uid": uid
    })

    return jsonify({"status": "success"})

# ---------------- DELETE ----------------
@app.route('/delete/<id>')
def delete(id):
    db.collection('expenses').document(id).delete()
    return redirect('/')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        users = db.collection('users').where('email', '==', email).stream()

        for u in users:
            user = u.to_dict()
            if user['password'] == password:
                session['user'] = user['uid']
                session['email'] = email
                return redirect('/')

        return "Invalid credentials"

    return render_template("login.html")

# ---------------- SIGNUP ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        uid = email + "_uid"

        db.collection('users').add({
            "email": email,
            "password": password,
            "uid": uid
        })

        session['user'] = uid
        session['email'] = email

        return redirect('/')

    return render_template("signup.html")

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)