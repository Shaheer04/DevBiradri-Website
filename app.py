from flask import Flask, render_template, request
from flask_mail import Mail, Message

app = Flask(__name__)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = ''
app.config['MAIL_PASSWORD'] = ''
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['fullname']
        email = request.form['email']
        message = request.form['message']

        msg = Message(subject='Registration Completed!', sender='', recipients=[email])
        msg.body = f"Hello {name}, your registration is completed. We will get back to you soon. Thank you for registering with us."
        mail.send(msg)
        print(name, email, message)

    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)