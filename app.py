from datetime import datetime

from flask import Flask, render_template, request, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
from nlp_utils import preprocess
from joblib import load

'''
to create the project database, open terminal
- type python and press enter
- type 
    from app import app, db
    with app.app_context():
        db.create_all()
- enter twice to confirm
'''


# models for database

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(64), nullable=False)
    created_on = db.Column(db.DateTime, default=datetime.now)

    def __str__(self):
        return f'{self.username}'


class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('predictions', lazy=True))
    message = db.Column(db.String(120), nullable=False)
    prediction = db.Column(db.String(120), nullable=False)
    created_on = db.Column(db.DateTime, default=datetime.now)

    def __str__(self):
        return f'{self.message} is predicted to be {self.prediction}'


class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    address = db.Column(db.String(120), unique=True, nullable=False)
    contact = db.Column(db.String(120), unique=True, nullable=False)
    specialization = db.Column(db.String(64), nullable=False)
    created_on = db.Column(db.DateTime, default=datetime.now)

    def __str__(self):
        return f'{self.name}'


def generate_50_fake_doctors():
    from faker import Faker
    from random import choice
    fake = Faker()
    for i in range(50):
        name = fake.name()
        address = fake.address()
        contact = fake.phone_number()
        # specialization for depression
        specialization = ['psychiatrist', 'psychologist', 'counselor', 'therapist', ]
        doctor = Doctor(name=name, address=address, contact=contact, specialization=choice(specialization))
        db.session.add(doctor)
        db.session.commit()

        # flask code starts here


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.sqlite'
    app.config['SQLALCHEMY_ECHO'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = 'su pers ecre tkey that nobo dyk nows'
    db.init_app(app)
    return app


app = create_app()


def create_login_session(user: User):
    session['id'] = user.id
    session['username'] = user.username
    session['email'] = user.email
    session['is_logged_in'] = True


def destroy_login_session():
    if 'is_logged_in' in session:
        session.clear()


@app.route('/')
def index():
    return render_template('index.html')


# froute
@app.route('/login', methods=['GET', 'POST'])
def login():
    errors = {}
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        print("LOGGIN IN", email, password)
        if password and email:
            if len(email) < 11 or '@' not in email:
                errors['email'] = 'Email is Invalid'
            if len(errors) == 0:
                user = User.query.filter_by(email=email).first()
                if user is not None:
                    print("user account found", user)
                    if user.password == password:
                        create_login_session(user)
                        flash('Login Successfull', "success")
                        return redirect('/form')
                    else:
                        errors['password'] = 'Password is invalid'
                else:
                    errors['email'] = 'Account does not exists'
        else:
            errors['email'] = 'Please fill valid details'
            errors['password'] = 'Please fill valid details'
    return render_template('login.html', errors=errors)


@app.route('/register', methods=['GET', 'POST'])
def register():
    errors = []
    if request.method == 'POST':  # if form was submitted
        username = request.form.get('username')
        email = request.form.get('email')
        pwd = request.form.get('password')
        cpwd = request.form.get('confirmpass')
        print(username, email, pwd, cpwd)
        if username and email and pwd and cpwd:
            if len(username) < 2:
                errors.append("Username is too small")
            if len(email) < 11 or '@' not in email:
                errors.append("Email is invalid")
            if len(pwd) < 6:
                errors.append("Password should be 6 or more chars")
            if pwd != cpwd:
                errors.append("passwords do not match")
            if len(errors) == 0:
                user = User(username=username, email=email, password=pwd)
                db.session.add(user)
                db.session.commit()
                flash('user account created', 'success')
                return redirect('/login')
        else:
            errors.append('Fill all the fields')
            flash('user account could not be created', 'warning')
    return render_template('register.html', error_list=errors)


def predict_depression(message):
    cleaned_message = preprocess(message)
    model = load('models/svc_cv_model.joblib')
    prediction = model.predict([cleaned_message])
    return prediction[0]


@app.route('/form', methods=['GET', 'POST'])
def form():
    if 'is_logged_in' not in session:
        return redirect('/login')
    errors = {}
    if request.method == 'POST':
        message = request.form.get('message')
        print(message)
        if message:
            if len(message) < 10:
                errors['message'] = 'Message is too small'
            if len(errors) == 0:
                prediction = predict_depression(message)
                prediction = Prediction(user_id=session['id'], message=message, prediction=prediction)
                db.session.add(prediction)
                db.session.commit()
                flash('prediction saved', 'success')
                return redirect('/prediction')
        else:
            errors['message'] = 'Please fill valid details'
            errors['prediction'] = 'Please fill valid details'
    return render_template('form.html', errors=errors)


@app.route('/prediction')
def prediction():
    if 'is_logged_in' not in session:
        return redirect('/login')
    predictions = Prediction.query.filter_by(user_id=session['id']).all()
    return render_template('prediction.html', predictions=predictions)


@app.route('/doctors')
def doctors():
    doctors = Doctor.query.all()
    return render_template('doctors.html', doctors=doctors)


@app.route('/logout')
def logout():
    destroy_login_session()
    flash('You are logged out', 'success')
    return redirect('/')


if __name__ == '__main__':
    # create database tables if not exists and run the app
    with app.app_context():
        db.create_all()
        # generate_50_fake_doctors()
        print("database created")
    app.run(debug=True, host='0.0.0.0')
