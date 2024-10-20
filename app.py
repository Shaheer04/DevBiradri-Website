from flask import Flask, render_template, request,redirect, url_for, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
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


app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(debug=True)