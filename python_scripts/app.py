from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, validators
from bson.objectid import ObjectId
import random
import string
from chatbot import initialize_cohere, extract_text_from_pdf, split_text_into_chunks, query_cohere

app = Flask(__name__)
app.config.from_object('config.Config')
mongo = PyMongo(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize the Cohere API client and load the PDF chunks

pdf_text = extract_text_from_pdf(r'C:\student_Thingy\student_Thingy\studentHandbook.pdf')
pdf_chunks = split_text_into_chunks(pdf_text)

# User model
class User(UserMixin):
    def __init__(self, email, password_hash, id=None):
        self.email = email
        self.password_hash = password_hash
        self.id = id 

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        return None
    return User(email=user['email'], password_hash=user['password'], id=user['_id'])

# Registration form
class RegistrationForm(FlaskForm):
    email = StringField('Email', [validators.Length(min=6, max=35), validators.Email()])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.Length(min=6, max=25),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')

# Login form
class LoginForm(FlaskForm):
    email = StringField('Email', [validators.DataRequired(), validators.Email()])
    password = PasswordField('Password', [validators.DataRequired()])

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        password_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user_id = mongo.db.users.insert_one({
            'email': form.email.data,
            'password': password_hash
        }).inserted_id
        user = User(email=form.email.data, password_hash=password_hash, id=user_id)
        login_user(user)
        flash('You are now registered and logged in', 'success')
        return redirect(url_for('dashboard'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user_data = mongo.db.users.find_one({'email': form.email.data})
        if user_data and bcrypt.check_password_hash(user_data['password'], form.password.data):
            user = User(email=user_data['email'], password_hash=user_data['password'], id=user_data['_id'])
            login_user(user)
            flash('You are now logged in', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user() 
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    forms = mongo.db.forms.find({'creator': current_user.id})
    return render_template('dashboard.html', forms=forms)

@app.route('/create_form', methods=['GET', 'POST'])
@login_required
def create_form():
    if request.method == 'POST':
        form_data = request.json
        slug = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        form_id = mongo.db.forms.insert_one({
            'title': form_data['title'],
            'description': form_data['description'],
            'questions': form_data['questions'],
            'creator': current_user.id,
            'slug': slug
        }).inserted_id
        return jsonify({'form_id': str(form_id), 'slug': slug})
    return render_template('create_form.html')

@app.route('/form/<slug>', methods=['GET', 'POST'])
def view_form(slug):
    form = mongo.db.forms.find_one({'slug': slug})
    if not form:
        return 'Form not found', 404
    if request.method == 'POST':
        entry = request.json
        entry['form_id'] = form['_id']
        mongo.db.entries.insert_one(entry)
        return jsonify({'message': 'Form submitted successfully'})
    return render_template('view_form.html', form=form)

@app.route('/edit_form/<form_id>', methods=['GET', 'POST'])
@login_required
def edit_form(form_id):
    form = mongo.db.forms.find_one({"_id": ObjectId(form_id), "creator": current_user.id})
    if not form:
        abort(404)

    if request.method == 'POST':
        form_data = request.json
        mongo.db.forms.update_one(
            {"_id": ObjectId(form_id)},
            {"$set": {
                "title": form_data['title'],
                "description": form_data['description'],
                "questions": form_data['questions']
            }}
        )
        return jsonify({"message": "Form updated successfully"})
    else:
        return jsonify({"message": "Request must be in JSON format"}), 400


@app.errorhandler(404)
def page_not_found(error):
    return '404 Error: Page not found', 404

@app.errorhandler(500)
def internal_server_error(error):
    return '500 Error: Internal Server Error', 500


@app.route('/form/<form_id>/delete', methods=['POST'])
@login_required
def delete_form(form_id):
    
    mongo.db.forms.delete_one({'_id': ObjectId(form_id), 'creator': current_user.id})
    return jsonify({'message': 'Form deleted successfully'})

@app.route('/chat')
def chat_response():
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get("message")
    if user_message:
        response = query_cohere(cohere_client, pdf_chunks, user_message)
        return jsonify({"response": response})
    return jsonify({"response": "No message received"})

if __name__ == '__main__':
    app.run(debug=True)
