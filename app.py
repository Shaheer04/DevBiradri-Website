from flask import Flask, render_template, request,redirect, url_for, jsonify, flash, session
from pymongo import MongoClient
from bson.objectid import ObjectId
from functools import wraps
from dotenv import load_dotenv,find_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def evnet_register():
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
                send_email(form_data['email'], "Registration Confirmation", 'email_template.html', name=form_data['fullname'])
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
        send_email(email, "Newsletter Subscription Confirmation", 'newsletter.html')
    except Exception as e:
        print(f"Failed to send email: {e}")
    
    return jsonify({"status": "success", "message": "Subscribed successfully"}), 200

@app.route('/success')
def success():
    return jsonify({"status": "sucess", "message": "Sucessfully Registered!, Check your email for confirmation"}), 200

@app.route('/dashboard-table')
@login_required
def get_table():
    return render_template("table.html")

@app.route('/dashboard-events')
@login_required
def add_events():
    return render_template("add_events.html")

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    print("Admin login route accessed")  # Debug print
    if 'admin_logged_in' in session:
        print("Admin already logged in, redirecting to dashboard")  # Debug print
        return redirect(url_for('admin_dashboard'))
    
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
            return redirect(url_for('admin_dashboard'))
        else:
            print("Invalid credentials")  # Debug print
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Fetch data for the dashboard
    #form_submissions = collection.find().limit(10)  # Last 10 form submissions
    #newsletter_subscribers = newsletter_collection.find().limit(10)  # Last 10 newsletter subscribers
    return render_template('dashboard.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/events')
def get_events():
    return render_template('events.html')


if __name__ == '__main__':
    app.run(debug=True)