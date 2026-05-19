from flask import Flask, render_template, request, redirect
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

app = Flask(__name__)

# Firebase setup
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

@app.route('/')
def index():

    expenses_ref = db.collection('expenses')
    docs = expenses_ref.stream()

    expenses = []
    total = 0

    category_totals = {}

    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id

        amount = float(data['amount'])

        total += amount

        category = data['category']

        if category in category_totals:
            category_totals[category] += amount
        else:
            category_totals[category] = amount

        expenses.append(data)

    return render_template(
        'index.html',
        expenses=expenses,
        total=total,
        category_totals=category_totals
    )

@app.route('/add', methods=['POST'])
def add_expense():

    title = request.form['title']
    amount = request.form['amount']
    category = request.form['category']

    db.collection('expenses').add({
        'title': title,
        'amount': amount,
        'category': category
    })

    return redirect('/')

@app.route('/delete/<id>')
def delete_expense(id):

    db.collection('expenses').document(id).delete()

    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)