from flask import Flask, render_template, request,redirect, url_for, jsonify, flash, session
from flask_paginate import Pagination, get_page_parameter
from pymongo import MongoClient
from bson.objectid import ObjectId
from functools import wraps
from dotenv import load_dotenv,find_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/uploads/events'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

load_dotenv(find_dotenv())
mongo_url = os.getenv('MONGO_URL')
username = os.getenv('SMTP_USERNAME')
password = os.getenv('SMTP_PASSWORD')
smtp_server = os.getenv('SMTP_SERVER')
smtp_port = os.getenv('SMTP_PORT')

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')


app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Connect to MongoDB
client = MongoClient(mongo_url)
db = client['Cluster0']
collection = db['registration_form_submissions']
newsletter_collection = db['newsletter_subscribers']

def send_email(recipient, subject, template, **kwargs):
    sender_email = username
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = recipient

    # Create the HTML version of your message
    html = render_template(template, **kwargs)
    
    # Turn these into plain/html MIMEText objects
    part = MIMEText(html, "html")
    
    # Add HTML part to MIMEMultipart message
    message.attach(part)
    
    # Send the email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()  # Secure the connection
        server.login(username, password)
        server.sendmail(sender_email, recipient, message.as_string())

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    current_date = datetime.now()
    
    # Get upcoming events
    upcoming_events = list(db.events.find({
        'date': {'$gte': current_date}
    }).sort('date', 1).limit(3))
    
    # Get past events
    past_events = list(db.events.find({
        'date': {'$lt': current_date}
    }).sort('date', -1).limit(3))
    
    return render_template('index.html',
                         upcoming_events=upcoming_events,
                         past_events=past_events)

@app.route('/register', methods=['GET', 'POST'])
def event_register():
    if request.method == 'POST':
            # Extract form data
            form_data = {
                'fullname': request.form.get('fullname'),
                'email': request.form.get('email'),
                'phone': request.form.get('phone'),
                'gender': request.form.get('gender'),
                'profession': request.form.get('profession'),
                'institute_name': request.form.get('institute-name'),
                'linkedin_link': request.form.get('linkedin-link'),
                'heard_about_us': request.form.get('heared-us'),
                'expectations': request.form.get('message'),
                'joined_whatsapp': request.form.get('ws-group')
            }
            
            #Check if email is already registered
            if collection.find_one({'email': form_data['email']}):
                return jsonify({"status": "error", "message": "Email already registered"}), 400
            
            # Save data to MongoDB
            result = collection.insert_one(form_data)

            try:
                send_email(form_data['email'], "Registration Confirmation", 'email_templates/event_registered.html', name=form_data['fullname'])
            except Exception as e:
                print(f"Failed to send email: {e}")
            
            # Redirect to a success page or back to the form
            return redirect(url_for('success'))
    
    return render_template('register.html')

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('newsletter-mail')
    
    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400
    
    # Check if email already exists
    if newsletter_collection.find_one({"email": email}):
        return jsonify({"status": "error", "message": "Email already subscribed"}), 400
    
    # Save email to MongoDB
    newsletter_collection.insert_one({"email": email})
    
    # Send confirmation email
    try:
        send_email(email, "Newsletter Subscription Confirmation", 'email_templates/newsletter.html')
    except Exception as e:
        print(f"Failed to send email: {e}")
    
    return jsonify({"status": "success", "message": "Subscribed successfully"}), 200

@app.route('/success')
def success():
    return jsonify({"status": "sucess", "message": "Sucessfully Registered!, Check your email for confirmation"}), 200

@app.route('/dashboard-table')
@login_required
def get_table():
    projection = {
        '_id': 0,  # Exclude the _id field
        'fullname': 1,
        'email': 1,
        'phone': 1,
        'profession': 1,
        'institute_name': 1
    }
    
    # Retrieve only specified fields from MongoDB
    registrations = db.registration_form_submissions.find({}, projection)
    return render_template("/dashboard/table.html", registrations=registrations)

@app.route('/dashboard-events')
@login_required
def add_events():
    return render_template("/dashboard/add_events.html")

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    print("Admin login route accessed")  # Debug print
    if 'admin_logged_in' in session:
        print("Admin already logged in, redirecting to dashboard")  # Debug print
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        print("POST request received")  # Debug print
        email = request.form.get('email')
        password = request.form.get('password')
        
        print(f"Received email: {email}")  # Debug print
        print(f"Expected email: {ADMIN_EMAIL}")  # Debug print
        print(f"Passwords match: {password == ADMIN_PASSWORD}")  # Debug print
        
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            print("Credentials correct, setting session")  # Debug print
            session['admin_logged_in'] = True
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            print("Invalid credentials")  # Debug print
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/admin/dashboard')
@login_required
def dashboard():
    # Fetch statistics for dashboard
    stats = {
        "total_events": db.events.count_documents({}),
        "newsletter_subscribers": db.subscribers.count_documents({}),
        "upcoming_events": db.events.count_documents({"date": {"$gte": datetime.now()}})
    }
    
    # Fetch latest events
    latest_events = db.events.find().sort("date", -1).limit(5)
    
    # Fetch recent registrations
    recent_registrations = db.registrations.aggregate([
        {
            "$lookup": {
                "from": "events",
                "localField": "event_id",
                "foreignField": "_id",
                "as": "event"
            }
        },
        {"$sort": {"registration_date": -1}},
        {"$limit": 6}
    ])
    
    return render_template("dashboard/dashboard.html", 
                         stats=stats, 
                         latest_events=latest_events,
                         recent_registrations=recent_registrations)

@app.route('/admin/logout')
@login_required
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/publish-event', methods=['GET', 'POST'])
@login_required  # If you have authentication in place
def publish_event():

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    if 'event_poster' in request.files:
        file = request.files['event_poster']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            poster_path = f'uploads/events/{filename}'
        else:
            poster_path = 'sassets/img/event-placeholder.jpg'

        fee = request.form.get('event_fee', '')
        try:
            fee = float(fee) if fee.strip() else 0.0
        except ValueError:
            fee = 0.0

    event_data = {
        'name': request.form.get('event_name'),
        'date': datetime.strptime(request.form.get('event_date'), '%Y-%m-%d'),
        'time': request.form.get('event_time'),
        'event_type': request.form.get('event_type'),
        'capacity': request.form.get('event_capacity'),
        'location': request.form.get('event_location'),
        'registration_deadline': request.form.get('registration_deadline'),
        'registration_link': request.form.get('registration_link'),
        'fee':fee,
        'description': request.form.get('event_description'),
        'additional_info': request.form.get('additional_info'),
        'poster_image': poster_path,
        'created_at': datetime.utcnow()
    }

    db.events.insert_one(event_data)
    flash('Event published successfully!', 'success')
    return redirect(url_for('events_page'))

@app.route('/events')
def events_page():
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 8  # Number of events per page

    # Calculate the number of documents to skip
    skip = (page - 1) * per_page

    # Fetch total number of events
    total = db.events.count_documents({})

    # Fetch events for the current page
    events = list(db.events.find().sort('date', -1).skip(skip).limit(per_page))

    # Create pagination object
    pagination = Pagination(page=page, total=total, per_page=per_page, css_framework='bootstrap4')

    return render_template('events.html', events=events, pagination=pagination)

@app.route('/event/<event_id>')
def event_detail(event_id):
    # Fetch the specific event from database using event_id
    event = db.events.find_one({'_id': ObjectId(event_id)})
    if not event:
        abort(404)
    return render_template('event_detail.html', event=event)


if __name__ == '__main__':
    app.run(debug=True)