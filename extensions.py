# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

db    = SQLAlchemy()
login = LoginManager()
bcrypt = Bcrypt()

login.login_view     = "auth.login_page"
login.login_message  = "Please log in to use Synapse."
login.login_message_category = "info"