#                   Similar al almacén de herramientas del Sistema. Inicializa todas las extensiones de Flask que necesita la aplicación
#                   (base de datos, autenticación, correors), pero no las confifura, es como tener las herraminetas lsitas pero sin enchufarlas aun


from flask_sqlalchemy import SQLAlchemy     # Importa "SQLAlchemy" qu es la herramienta para comunicarse con la base de datos de manera fácil (ORM = Obect Relational Mapping)
from flask_login import LoginManager        # Importa "LoginManager" que maneja todo lo relacionado con inicios de sesión, usuarios logueados, etc
from flask_mail import Mail                 # Para enviar correos electrónicos (como códigos 2FA)


db = SQLAlchemy()               # Instancia de SQLAlchemy 
login_manager = LoginManager()  # Instancia del gestor de login
mail = Mail()                   # Instancia del sistema de correos



# Configuración opcional para Flask-Login
login_manager.login_view = 'auth.login' # <-- IMPORTANTE: Nombre del endpoint de login en el Blueprint 'auth'
login_manager.login_message_category = 'info'   # Define el tipo de mensaje que se mostrará
login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.'    #Define el mensaje exacto que verá el usuario cuando lo redirijan al login

# Función para cargar el usuario (requerida por Flask-Login)
@login_manager.user_loader
def load_user(user_id):
    from .models import User # Importa el modelo User aquí para evitar importaciones circulares
    return User.query.get(int(user_id))
