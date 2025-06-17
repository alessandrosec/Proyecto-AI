# your_flask_app/blueprints/main.py

#                   Es el archivo MÁS IMPORTANTE del sistema.
#                   MANEJA las FUNCIONE PRINCIPALES:
#                       - Mostrar la página de inicio con cursos
#                       - Procesar solicitudes de becas
#                       - Mostrar el estado de las solicitudes



from flask import Blueprint, render_template, flash, redirect, url_for, request     # Importa las herramientas básicas de Flask
from flask_login import login_required, current_user                                # Importa herramientas de Autenticación
from ..models import Estudiante, Inscripcion                                        # Importa los modelos de datos (estudiantes e inscripciones)
from ..forms import EstudianteForm, InscripcionApprovalForm                         # Importa los formularios que usará
from ..extensions import db                                                         # Importa "db" para hablar con la base de datos
from ..decorators import role_required                                              # Importa el decorador para verificar roles de usuario
from datetime import date                                                           # Importa las herramientas para trabajar con fechas
import bleach                                                                       # Para limpiar datos maliciosos
# ✅ Importa los diccionarios desde data.py
from ..data import LATAM_PAISES_CIUDADES, NOMBRE_DOCUMENTO_POR_PAIS                 # Importa los diccionarios de países/ciudades y nombres de documentos




#                    CREAR EL BLUEPRINT PRINCIPAL
# Crea la sección PRINCIPAL del SISTEMA que usa templates de .../templates
main_bp = Blueprint('main', __name__, template_folder='../templates')




#                   PÁGINA DE INICIO
# Ejecuta cuando va a la página principal (/)
@main_bp.route('/')
@main_bp.route('/index') # También ejecuta cuando va a /index

# Inicia de la Página Principal
def index():
    return render_template('index.html', title='Inicio')




#                   DETALLES DEL CURSO
@main_bp.route('/cursos/<slug>')
def curso_detalle(slug):
    cursos = {
        'programadores-junior': {
            'nombre': 'PROGRAMADORES JUNIOR',
            'descripcion': 'Impulsa tu futuro. Aprender a Programar con una beca 100% gratuita y adquiere nuevas habilidades digitales',
            
            # Agregué esto ya que el código estaba hardokeado, entonces los requisitos que se editaban aparecían en ambos apartados
            'requisitos': [
                'Tener entre 18 a 35 años'
                'Graduado a Niverl Medio'
            ],
            'imagen': 'python.png',
            'slug': 'programacion-python'

        },
        'ciberseguridad': {
            'nombre': 'PROGRAMA DE CERTIFICACIÓN EN CIBERSEGURIDAD',
            'descripcion': 'Conoce todo lo que aprenderás en el programa de certificación en ciberseguridad de IRSI',
            
            # Agregué requitos al igual que arriba
            'requisitos': [
                'La capacidad de programar en varios lenguajes es útil para entender mejor los sistemas y aplicaciones que se deben proteger.'
                'Los conocimientos de redes son esenciales para entender cómo se conectan los sistemas y cómo se pueden proteger las redes contra posibles amenazas.'
                'Es importante tener un conocimiento sólido de sistemas operativos como Windows y Linux para identificar vulnerabilidades en los sistemas y aplicaciones.'
            ],
            'imagen': 'flask.png',
            'slug': 'desarrollo-web-flask'
        }
    }
    curso = cursos.get(slug)
    if not curso:
        flash('El curso solicitado no existe.', 'danger')
        return redirect(url_for('main.index'))
    return render_template(
        'curso_detalle.html',
        title=curso['nombre'],
        curso=curso,
        curso_slug=curso['slug']  # <--- Esta línea es clave
    )




#                   SOLICITAR ADMISIÓN (Función más compleja)         
@main_bp.route('/solicitar_admision', methods=['GET', 'POST'])
@login_required
@role_required(['user', 'admin'])
def solicitar_admision():
    curso_slug = request.args.get('curso_slug')
    if not curso_slug:
        flash('Debes seleccionar un curso para solicitar admisión.', 'danger')
        return redirect(url_for('main.index'))

    estudiante = current_user.estudiante
    inscripcion_existente = None

    # Buscar inscripción existente a ese curso (si hay estudiante)
    if estudiante:
        inscripcion_existente = Inscripcion.query.filter_by(estudiante_id=estudiante.id, curso_slug=curso_slug).first()
        if inscripcion_existente:
            flash('Ya tienes una solicitud para este curso. Puedes editar tus datos.', 'info')

    form = EstudianteForm(obj=estudiante)
    if request.method == 'GET' and not form.correo.data:
        form.correo.data = current_user.username

    form.ciudad.choices = [(c, c) for c in LATAM_PAISES_CIUDADES.get(form.pais.data, [])]
    dni_label = NOMBRE_DOCUMENTO_POR_PAIS.get(form.pais.data, "Documento de Identificación")

    if form.validate_on_submit():

#       ACTUALIZAR DATOS DEL ESTUDIANTE
        # Actualizar datos del estudiante (si existe) o crear nuevo
        if estudiante:
            form.populate_obj(estudiante)

        #     
        else:
            estudiante = Estudiante(
                nombre=bleach.clean(form.nombre.data),
                apellidos=bleach.clean(form.apellidos.data),
                pais=bleach.clean(form.pais.data),
                ciudad=bleach.clean(form.ciudad.data),
                direccion=bleach.clean(form.direccion.data),
                grado=bleach.clean(form.grado.data),
                dni=bleach.clean(form.dni.data),
                fecha_nacimiento=form.fecha_nacimiento.data,
                correo=bleach.clean(form.correo.data),
                telefono=bleach.clean(form.telefono.data),
                anio_solicitud=form.anio_solicitud.data,
                user_id=current_user.id if current_user.role == 'user' else None,
                sexo=bleach.clean(form.sexo.data),
                motivo=bleach.clean(form.motivo.data),
                veracidad=form.veracidad.data
            )
            db.session.add(estudiante)
            db.session.flush()  # para obtener id

#       VALIDAR DATOS ÚNICOS
        # Validar duplicados por DNI/correo al crear
        if not inscripcion_existente:
            existing_dni = Estudiante.query.filter(Estudiante.dni == bleach.clean(form.dni.data), Estudiante.id != estudiante.id).first()
            if existing_dni:
                flash('Ya existe un estudiante con ese DNI.', 'danger')
                return render_template(
                    'add_student.html',
                    title='Solicitar Admisión',
                    form=form,
                    LATAM_PAISES_CIUDADES=LATAM_PAISES_CIUDADES,
                    NOMBRE_DOCUMENTO_POR_PAIS=NOMBRE_DOCUMENTO_POR_PAIS,
                    dni_label=dni_label
                )

            existing_correo = Estudiante.query.filter(Estudiante.correo == bleach.clean(form.correo.data), Estudiante.id != estudiante.id).first()
            if existing_correo:
                flash('Ya existe un estudiante con ese correo electrónico.', 'danger')
                return render_template(
                    'add_student.html',
                    title='Solicitar Admisión',
                    form=form,
                    LATAM_PAISES_CIUDADES=LATAM_PAISES_CIUDADES,
                    NOMBRE_DOCUMENTO_POR_PAIS=NOMBRE_DOCUMENTO_POR_PAIS,
                    dni_label=dni_label
                )

#       CRAR UNA INSCRIPCIÓN
        # Solo crear inscripción nueva si no existe para ese curso
        if not inscripcion_existente:
            nueva_inscripcion = Inscripcion(
                estudiante_id=estudiante.id,
                curso_slug=curso_slug,
                estado='pendiente'
            )
            db.session.add(nueva_inscripcion)
            flash('Solicitud de admisión enviada exitosamente.', 'success')
        else:
            flash('Datos actualizados. Ya tienes una inscripción para este curso.', 'info')

        db.session.commit()
        return redirect(url_for('main.mis_solicitudes'))

#   MOSTRAR FORMULARIO
    return render_template(
        'add_student.html',
        title='Solicitar Admisión',
        form=form,
        LATAM_PAISES_CIUDADES=LATAM_PAISES_CIUDADES,
        NOMBRE_DOCUMENTO_POR_PAIS=NOMBRE_DOCUMENTO_POR_PAIS,
        dni_label=dni_label
    )




#                   VER MIS SOLICITUDES
@main_bp.route('/mis_solicitudes')
@login_required
@role_required(['user'])
def mis_solicitudes():
    estudiante = current_user.estudiante
    inscripciones = []
    if estudiante:
        inscripciones = Inscripcion.query.filter_by(estudiante_id=estudiante.id).order_by(Inscripcion.fecha_inscripcion.desc()).all()
    return render_template('mis_solicitudes.html', estudiante=estudiante, inscripciones=inscripciones)
