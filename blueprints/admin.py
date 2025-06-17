# your_flask_app/blueprints/admin.py


#       Archivo que contiene TODAS las FUNCIONALIDADES que puede USAR los ADMINISTRADORES del sistema
#       Este es como el "PANEL DE CONTROL" para gestionar estudiantes y sus solicitudes de becas


from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required                                              # Solo usuarios logueados pueden acceder
from ..decorators import role_required                                              # Solo usuarios con Rol específico pueden acceder
from ..models import Estudiante, Inscripcion                                        # Los modelos de los datos
from ..forms import EstudianteForm, InscripcionApprovalForm, UploadExcelForm        # Formulario para aprobar/rechazar solicitudes
from ..extensions import db                                                         # Para interactuar con la base de datos
import bleach                                                                       # Para limpiar la entrada del usuario
# NUEVAS IMPORTACIONES PARA EXCEL
import pandas as pd
import os
from werkzeug.utils import secure_filename
from datetime import datetime, date


#                   CREACIÓN DE BLUEPRINTS 

# Crea una instancia de Blueprint. Usamos 'admin' como nombre.
admin_bp = Blueprint('admin', __name__, 
                    template_folder='../templates/admin',   # Las páginas HTML están aquí
                    url_prefix='/admin')                    # Todas la rutas empiezan con /admin/ ||  # Puedes definir el prefijo aquí o en app.py



#                   DASHBOARD PRINCIPAL
# Ruta para el panel de administrador
@admin_bp.route('/')            # Esta ruta se accederá como /admin/
@admin_bp.route('/dashboard')   # Esta ruta se accederá como /admin/dashboard
@login_required                 # Solo permite acceder si está logueado
@role_required(['admin'])       # Solo deja pasar si es Administrador

# Empieza función que se ejecutará
def dashboard():
    # Puedes añadir datos relevantes para el dashboard aquí, como estadísticas, etc.
    total_estudiantes = Estudiante.query.count()                                            # Cuenta cuántos estudiantes hay y los guarda en total_estudiantes
    inscripciones_pendientes = Inscripcion.query.filter_by(estado='pendiente').count()      # Cuántas solicitudes están pendientes de revisión
    return render_template('dashboard.html',                                #  Muestra la página dashboard.html
                        title='Panel de Administrador',                     # Le pasa el título de la página
                        total_estudiantes=total_estudiantes,                # Le pasa el número de estudiantes
                        inscripciones_pendientes=inscripciones_pendientes)  # Le pasa el número de solicitudes pendientes



#                   VER LISTA DE ESTUDIANTES
# Ruta para listar estudiantes
@admin_bp.route('/students')
@login_required
@role_required(['admin']) # Solo administradores

# Inicia función para mostrar estudiantes
def student_list():
    students = Estudiante.query.all()                                                               # Obtiene TODOS los estudiantes de la BD y los guarda en students
    return render_template('student_list.html', title='Lista de Estudiantes',
                            students=students)    # Muestra la página student_list.html y le pasa la lista de estudiantes



#                   ELIMINAR ESTUDIANTE
# Ruta para eliminar estudiante (solo admin)
@admin_bp.route('/delete_student/<int:id>', methods=['POST'])
@login_required
@role_required(['admin'])

# Inicia la función que recibe el "id" del estudiante a eliminar
def delete_student(id):
    student = Estudiante.query.get_or_404(id) # BUsca el estudinte con ese ID, sino lo encuentra muestre "error 404"
    try:
        db.session.delete(student)
        db.session.commit()
        flash('Estudiante eliminado exitosamente.', 'success')
        # current_app.logger.info(f'Estudiante eliminado: {student.nombre} {student.apellidos}')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar estudiante: {e}', 'danger')
        # current_app.logger.error(f'Error al eliminar estudiante: {e}')
    return redirect(url_for('admin.student_list')) # Redirige a la lista de estudiantes del blueprint 'admin'



#                   VER TODAS LAS SOLICITUDES
# Ruta para gestionar inscripciones (aprobar/rechazar)
@admin_bp.route('/manage_inscripciones')
@login_required
@role_required(['admin'])

# Inicia función para gestionar solicitudes
def manage_inscripciones():

    # Obtener todas las inscripciones o filtrarlas
    inscripciones = Inscripcion.query.all()

    # Muestra la página con todas las solicitudes
    return render_template('manage_inscripcion.html',
                            title='Gestión de Inscripciones',
                            inscripciones=inscripciones)



#                   APROBAR O RECHAZAR UNA SOLICITUD
# Ruta para cambiar el estado de una inscripción
@admin_bp.route('/inscripcion/<int:inscripcion_id>/update_status', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])

# Inicia la función que recibe el ID de la solicitud
def update_inscripcion_status(inscripcion_id):
    inscripcion = Inscripcion.query.get_or_404(inscripcion_id)
    form = InscripcionApprovalForm(obj=inscripcion) # Pre-rellena el formulario con el estado actual

    # el usuario envió el formulario y todos los datos son correctos?
    if form.validate_on_submit(): 
        inscripcion.estado = form.estado.data # Cambiar el estado: aprobada/rechazada
        inscripcion.razon_rechazo = bleach.clean(form.razon_rechazo.data) if form.razon_rechazo.data else None
        
        try:
            db.session.commit()
            flash(f'Estado de inscripción {inscripcion.id} actualizado a {inscripcion.estado}.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la inscripción: {e}', 'danger')
            # current_app.logger.error(f'Error al actualizar inscripción {inscripcion.id}: {e}')
        return redirect(url_for('admin.manage_inscripciones'))

    return render_template('admin/update_inscripcion_status.html',
                            title='Actualizar Inscripción',
                            form=form, inscripcion=inscripcion) # Necesitarás crear esta plantilla


#                   NUEVA FUNCIÓN: Procesar archivo Excel (G)
@admin_bp.route('/upload_excel', methods=['POST'])
@login_required
@role_required(['admin'])
def upload_excel():
    form = UploadExcelForm()
    
    if form.validate_on_submit():
        try:
            # Obtener el archivo subido
            file = form.excel_file.data
            filename = secure_filename(file.filename)
            
            # Crear directorio temporal si no existe
            upload_folder = 'temp_uploads'
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            # Guardar archivo temporalmente
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            
            # Leer el archivo Excel con pandas
            try:
                df = pd.read_excel(file_path)
            except Exception as e:
                flash(f'Error al leer el archivo Excel: {str(e)}', 'danger')
                os.remove(file_path)  # Limpiar archivo temporal
                return redirect(url_for('admin.student_list'))
            
            # Validar columnas requeridas
            required_columns = ['Nombre', 'Apellidos', 'DNI', 'Correo', 'Telefono', 
                                'Pais', 'Ciudad', 'Direccion', 'Grado', 'Fecha_Nacimiento', 
                                'Sexo', 'Motivo']
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                flash(f'Faltan las siguientes columnas en el Excel: {", ".join(missing_columns)}', 'danger')
                os.remove(file_path)
                return redirect(url_for('admin.student_list'))
            
            # Contadores para el reporte
            estudiantes_agregados = 0
            estudiantes_duplicados = 0
            errores = []
            
            # Procesar cada fila del Excel
            for index, row in df.iterrows():
                try:
                    # Validar datos básicos
                    if pd.isna(row['Nombre']) or pd.isna(row['Apellidos']) or pd.isna(row['DNI']) or pd.isna(row['Correo']):
                        errores.append(f'Fila {index + 2}: Faltan datos obligatorios (Nombre, Apellidos, DNI, Correo)')
                        continue
                    
                    # Limpiar y preparar datos
                    dni = str(row['DNI']).strip()
                    correo = str(row['Correo']).strip().lower()
                    
                    # Verificar si ya existe un estudiante con este DNI o correo
                    existing_student = Estudiante.query.filter(
                        (Estudiante.dni == dni) | (Estudiante.correo == correo)
                    ).first()
                    
                    if existing_student:
                        estudiantes_duplicados += 1
                        continue
                    
                    # Procesar fecha de nacimiento
                    try:
                        if isinstance(row['Fecha_Nacimiento'], str):
                            fecha_nacimiento = datetime.strptime(row['Fecha_Nacimiento'], '%Y-%m-%d').date()
                        else:
                            fecha_nacimiento = row['Fecha_Nacimiento'].date()
                    except:
                        errores.append(f'Fila {index + 2}: Formato de fecha inválido. Use YYYY-MM-DD')
                        continue
                    
                    # Crear nuevo estudiante
                    nuevo_estudiante = Estudiante(
                        nombre=bleach.clean(str(row['Nombre']).strip()),
                        apellidos=bleach.clean(str(row['Apellidos']).strip()),
                        dni=bleach.clean(dni),
                        correo=bleach.clean(correo),
                        telefono=bleach.clean(str(row['Telefono']).strip()) if not pd.isna(row['Telefono']) else '',
                        pais=bleach.clean(str(row['Pais']).strip()) if not pd.isna(row['Pais']) else '',
                        ciudad=bleach.clean(str(row['Ciudad']).strip()) if not pd.isna(row['Ciudad']) else '',
                        direccion=bleach.clean(str(row['Direccion']).strip()) if not pd.isna(row['Direccion']) else '',
                        grado=bleach.clean(str(row['Grado']).strip()) if not pd.isna(row['Grado']) else '',
                        fecha_nacimiento=fecha_nacimiento,
                        sexo=bleach.clean(str(row['Sexo']).strip()) if not pd.isna(row['Sexo']) else 'Otro',
                        motivo=bleach.clean(str(row['Motivo']).strip()) if not pd.isna(row['Motivo']) else 'Cargado desde Excel',
                        veracidad=True,  # Asumimos que los datos del Excel son verídicos
                        anio_solicitud=datetime.now().year,
                        user_id=None  # No se asocia a ningún usuario específico
                    )
                    
                    db.session.add(nuevo_estudiante)
                    estudiantes_agregados += 1
                    
                except Exception as e:
                    errores.append(f'Fila {index + 2}: Error al procesar - {str(e)}')
                    continue
            
            # Confirmar cambios en la base de datos
            try:
                db.session.commit()
                
                # Crear mensaje de éxito
                mensaje = f'Procesamiento completado: {estudiantes_agregados} estudiantes agregados'
                if estudiantes_duplicados > 0:
                    mensaje += f', {estudiantes_duplicados} duplicados omitidos'
                if errores:
                    mensaje += f', {len(errores)} errores encontrados'
                
                flash(mensaje, 'success')
                
                # Mostrar errores si los hay
                if errores:
                    for error in errores[:5]:  # Mostrar solo los primeros 5 errores
                        flash(error, 'warning')
                    if len(errores) > 5:
                        flash(f'... y {len(errores) - 5} errores más', 'warning')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al guardar en la base de datos: {str(e)}', 'danger')
            
            # Limpiar archivo temporal
            os.remove(file_path)
            
        except Exception as e:
            flash(f'Error inesperado al procesar el archivo: {str(e)}', 'danger')
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
    
    else:
        # Si el formulario no es válido, mostrar errores
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return redirect(url_for('admin.student_list'))
