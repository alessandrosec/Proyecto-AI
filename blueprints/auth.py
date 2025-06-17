# your_flask_app/blueprints/auth.py

#                   Es el archivo que maneja TODO lo relacionado con USUARIOS: "Registrarse", "Iniciar Sesión", 
#                   "Autenticaciónde dos factores (2FA)" y "Cerrar Sesión".

from flask import Blueprint, render_template, redirect, url_for, flash, request, session # Importa las herramientas básicas de Flask
from flask_login import login_user, logout_user, login_required, current_user            # Importa herramientas para manejar usuarios
from flask_mail import Message                                                           # Importa Message para crear y enviar correos electrónicos
from datetime import datetime, timedelta                                                 # Importa herramientas para trabajar con fechas y tiempos
import random                                                                            # Generar números aleatorios (como códigos 2FA de 6 dígitos)
import bleach                                                                            # Para limpiar texto malicioso que pueda enviar el usuario
from ..forms import LoginForm, TwoFactorForm, RegistrationForm                           # Importa los formularios que se usará
from ..models import User                                                                # Importa el modelo "User" (la plantilla de usuarios en la base de datos)
from ..extensions import db, mail                                                        # db para hablar con la base de datos y mail para enviar correos



#                   CREAR LA SECCIÓN DE AUTENTICACIÓN
# Crea una nueva sección llamada "auth"
# Le dice que use las páginas HTML de la carpeta "templates/auth"
auth_bp = Blueprint('auth', __name__, template_folder='../templates/auth') # Apunta a la subcarpeta de templates



#                   FUNCIÓN DE REGISTRO
# Ejecuta esta función cuando van a "/auth/register". Acepta GET (mostrar formulario) y POST (procesar registro).
@auth_bp.route('/register', methods=['GET', 'POST']) 

# Inicia la función de registro
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) # Redirige al index del blueprint 'main'
    form = RegistrationForm()
    if form.validate_on_submit():
        username = bleach.clean(form.username.data)
        password = form.password.data
        user = User(username=username, role='user')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('¡Felicidades, te has registrado exitosamente!', 'success')
        # app.logger.info(f'Nuevo usuario registrado: {username}') # Acceder al logger global
        return redirect(url_for('auth.login')) # Redirige al login del blueprint 'auth'
    return render_template('register.html', title='Registro', form=form)



#                   FUNCIÓN DE INICIAR SESIÓN
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) # Si está logueado lo envía a la página principal
    form = LoginForm()


    if form.validate_on_submit():
        username = bleach.clean(form.username.data)
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(form.password.data):

            # Si el usuario no existe o la contraseña está mal, muestra error y vuelve al login
            flash('Usuario o contraseña inválidos', 'danger')
            return redirect(url_for('auth.login')) # Redirige al login del blueprint 'auth'

        # Generar y enviar código 2FA
        two_factor_code = str(random.randint(100000, 999999))
        user.two_factor_code = two_factor_code
        user.two_factor_expiry = datetime.utcnow() + timedelta(minutes=5)
        db.session.commit()

        # Importar current_app para acceder a la configuración de MAIL_DEFAULT_SENDER
        from flask import current_app
        msg = Message('Código de Autenticación de Dos Factores',
                    sender=current_app.config['MAIL_DEFAULT_SENDER'],
                    recipients=[user.username])
        msg.body = f"Tu código de autenticación de dos factores es: {two_factor_code}\n\nEste código es válido por 5 minutos."

        try:
            mail.send(msg)
            flash('Se ha enviado un código 2FA a tu correo electrónico.', 'info')
            session['awaiting_2fa_user_id'] = user.id
            return redirect(url_for('auth.two_factor_auth')) # Redirige a 2FA del blueprint 'auth'
        except Exception as e:
            flash(f'Error al enviar el código 2FA: {e}', 'danger')
            # current_app.logger.error(f'Error al enviar 2FA a {user.username}: {e}')
            return redirect(url_for('auth.login'))

    return render_template('login.html', title='Iniciar Sesión', form=form)




#                   FUNCIÓN DE AUTENTICACIÓN DE DOS FACTORES
# Ejecuta cuando van a /auth/two_factor_auth
@auth_bp.route('/two_factor_auth', methods=['GET', 'POST'])

# Inicia la función 2FA
def two_factor_auth():

#   Si está loqueado lo manda a la página principal    
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

#   Recupera el ID del usuario que guardamos cuando envi+o el código
    user_id = session.get('awaiting_2fa_user_id')
    if not user_id:

#       Si no hay ID, significa que llegó sin pasar por el login, asi que lo regresa
        flash('Acceso denegado. Por favor, inicia sesión de nuevo.', 'danger')
        return redirect(url_for('auth.login'))


    user = User.query.get(user_id)
    if not user:

#       Si no existe el usuario, muestra error y regresa al login
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('auth.login'))

    form = TwoFactorForm()
    if form.validate_on_submit():
        entered_code = bleach.clean(form.code.data)
        if user.two_factor_code == entered_code and datetime.utcnow() < user.two_factor_expiry:
            login_user(user, remember=False)
            user.two_factor_code = None
            user.two_factor_expiry = None
            db.session.commit()
            session.pop('awaiting_2fa_user_id', None)
            flash('Autenticación exitosa.', 'success')
            # current_app.logger.info(f'Login exitoso para: {user.username}')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Código 2FA inválido o expirado.', 'danger')
            # current_app.logger.warning(f'Código 2FA inválido/expirado para: {user.username}')
            return redirect(url_for('auth.two_factor_auth'))

    return render_template('2fa.html', title='Autenticación de Dos Factores', form=form)




#                   FUNCIÓN CERRAR SESIÓN
@auth_bp.route('/logout')
@login_required
def logout():
    # current_app.logger.info(f'Usuario {current_user.username} ha cerrado sesión.')
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('main.index')) # Redirige al index del blueprint 'main'


"""             FLUJO COMPLETO DE AUTENTICACIÓN

Flujo Completo de Autenticación
1. Registro (/auth/register)

Usuario llena formulario (email, contraseña, confirmar contraseña)
Sistema crea usuario con contraseña encriptada
Lo envía al login

2. Login (/auth/login)

Usuario ingresa email y contraseña
Sistema verifica que exista y la contraseña sea correcta
Genera código de 6 dígitos aleatorio
Envía código por correo
Guarda temporalmente que este usuario está esperando 2FA
Lo envía a ingresar el código

3. Código 2FA (/auth/two_factor_auth)

Usuario ingresa el código de 6 dígitos
Sistema verifica que sea correcto y no haya expirado
Si está bien: lo loguea oficialmente
Si está mal: le da otra oportunidad

4. Logout (/auth/logout)

Usuario hace clic en "Cerrar Sesión"
Sistema lo desloguea
Lo envía a la página principal

            ¿Por qué es seguro?

Contraseñas encriptadas (nunca en texto plano)
Código 2FA temporal (expira en 5 minutos)
Verificaciones en cada paso
Limpieza de datos maliciosos
Manejo de errores para casos inesperados"""
