from flask import Flask, render_template, request, redirect
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

app = Flask(__name__)

# FIREBASE SETUP
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)

db = firestore.client()


@app.route('/')
def index():

    expenses_ref = db.collection('expenses')
    docs = expenses_ref.stream()

    expenses = []

    total = 0
    monthly_total = 0
    yearly_total = 0

    category_totals = {}

    # MONTH-WISE STORAGE
    monthly_data = {}

    current_month = datetime.now().month
    current_year = datetime.now().year

    for doc in docs:

        data = doc.to_dict()
        data['id'] = doc.id

        amount = float(data['amount'])

        total += amount

        # DATE FORMAT
        expense_date = datetime.strptime(
            data['date'],
            "%d-%m-%Y"
        )

        month_name = expense_date.strftime("%B")
        year = expense_date.year

        month_key = f"{month_name} {year}"

        # MONTHLY GRID
        if month_key not in monthly_data:

            monthly_data[month_key] = {
                "expenses": [],
                "total": 0
            }

        monthly_data[month_key]["expenses"].append(data)

        monthly_data[month_key]["total"] += amount

        # THIS MONTH TOTAL
        if (
            expense_date.month == current_month
            and expense_date.year == current_year
        ):
            monthly_total += amount

        # THIS YEAR TOTAL
        if expense_date.year == current_year:
            yearly_total += amount

        # CATEGORY TOTALS
        category = data['category']

        if category in category_totals:
            category_totals[category] += amount
        else:
            category_totals[category] = amount

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


@app.route('/add', methods=['POST'])
def add_expense():

    title = request.form['title']
    amount = request.form['amount']
    category = request.form['category']

    db.collection('expenses').add({

        'title': title,

        'amount': amount,

        'category': category,

        'date': datetime.now().strftime("%d-%m-%Y")

    })

    return redirect('/')


@app.route('/delete/<id>')
def delete_expense(id):

    db.collection('expenses').document(id).delete()

    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)