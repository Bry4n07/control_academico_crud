from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os
import random

app = Flask(__name__)
app.secret_key = 'clave_secreta_certificacion'

""""
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="control_colegio"
    )
"""
def get_db_connection():
    return mysql.connector.connect(
        host="mysql-255ba0d4-schoolu.c.aivencloud.com",
        port=19450,
        user="avnadmin",
        password="DB_PASSWORD",
        database="defaultdb"

    )
    
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('rol') == 'estudiante':
            return redirect(url_for('portal_estudiante'))
        return redirect(url_for('dashboard'))
    return render_template('colegio.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario_input = request.form.get('usuario', '').strip()
        password_input = request.form.get('password', '').strip()
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Validacion de acceso para personal administrativo o profesores
        cursor.execute("SELECT * FROM profesores WHERE usuario = %s", (usuario_input,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password_input):
            session['user_id'] = user['id']
            session['user_name'] = user['nombre']
            session['rol'] = user['rol']
            cursor.close()
            conn.close()
            return redirect(url_for('dashboard'))
            
        # Validacion de acceso alternativo para estudiantes por carnet
        cursor.execute("SELECT * FROM estudiantes WHERE carnet = %s", (usuario_input,))
        estudiante = cursor.fetchone()
        
        if estudiante and check_password_hash(estudiante['password'], password_input):
            session['user_id'] = estudiante['id']
            session['user_name'] = estudiante['nombre']
            session['rol'] = 'estudiante'
            cursor.close()
            conn.close()
            return redirect(url_for('portal_estudiante'))
            
        cursor.close()
        conn.close()
        return render_template('login.html', error_inicial="Usuario, carné o contraseña incorrectos")
        
    return render_template('login.html')

@app.route('/portal-estudiante')
def portal_estudiante():
    if 'user_id' not in session or session.get('rol') != 'estudiante':
        return redirect(url_for('login'))
        
    estudiante_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM estudiantes WHERE id = %s", (estudiante_id,))
    perfil = cursor.fetchone()
    
    # Obtencion de actas oficiales ordenadas por el semestre fijo de la asignatura
    cursor.execute("""
        SELECT m.nombre_materia, m.semestre, c.nota
        FROM asignaciones a
        JOIN materias m ON a.materia_id = m.id
        JOIN calificaciones c ON c.asignacion_id = a.id
        WHERE c.estudiante_id = %s
        ORDER BY m.semestre, m.nombre_materia
    """, (estudiante_id,))
    historial_notas = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('portal_estudiante.html', perfil=perfil, notas=historial_notas)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('rol') == 'estudiante':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Obtener total de profesores
    cursor.execute("SELECT COUNT(*) as total FROM profesores")
    total_profesores = cursor.fetchone()['total']
    
    # Lógica condicional: El Admin ve todo, el Profesor ve solo sus métricas
    if session.get('rol') == 'admin':
        # Total de cursos activos (todas las asignaciones)
        cursor.execute("SELECT COUNT(*) as total FROM asignaciones")
        total_cursos = cursor.fetchone()['total']
        
        # Total de notas registradas globales
        cursor.execute("SELECT COUNT(*) as total FROM calificaciones")
        total_notas = cursor.fetchone()['total']
    else:
        profesor_id = session['user_id']
        
        # Total de cursos asignados al profesor logueado
        cursor.execute("SELECT COUNT(*) as total FROM asignaciones WHERE profesor_id = %s", (profesor_id,))
        total_cursos = cursor.fetchone()['total']
        
        # Total de notas registradas por este profesor
        cursor.execute("""
            SELECT COUNT(c.id) as total 
            FROM calificaciones c
            JOIN asignaciones a ON c.asignacion_id = a.id
            WHERE a.profesor_id = %s
        """, (profesor_id,))
        total_notas = cursor.fetchone()['total']
        
    cursor.close()
    conn.close()
    
    # Pasamos los totales a la plantilla HTML
    return render_template('dashboard.html', 
                           total_profesores=total_profesores, 
                           total_cursos=total_cursos, 
                           total_notas=total_notas)

@app.route('/profesores', methods=['GET'])
def profesores():
    if 'user_id' not in session or session.get('rol') == 'estudiante': 
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nombre, usuario, rol FROM profesores ORDER BY id DESC")
    lista_profesores = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template('profesores.html', profesores=lista_profesores)

@app.route('/cursos_estudiantes', methods=['GET'])
def cursos_estudiantes():
    if 'user_id' not in session or session.get('rol') == 'estudiante': 
        return redirect(url_for('login'))
        
    profesor_logueado = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT id, nombre_materia, semestre FROM materias ORDER BY semestre, nombre_materia")
    all_materias = cursor.fetchall()
    
    if session.get('rol') == 'admin':
        cursor.execute("""
            SELECT a.id, m.nombre_materia as curso_nombre, m.semestre, a.seccion 
            FROM asignaciones a
            JOIN materias m ON a.materia_id = m.id
            ORDER BY m.semestre, m.nombre_materia
        """)
    else:
        cursor.execute("""
            SELECT a.id, m.nombre_materia as curso_nombre, m.semestre, a.seccion 
            FROM asignaciones a
            JOIN materias m ON a.materia_id = m.id
            WHERE a.profesor_id = %s
            ORDER BY m.semestre, m.nombre_materia
        """, (profesor_logueado,))
    all_cursos = cursor.fetchall()
    
    cursor.execute("SELECT id, carnet, nombre, correo, telefono, fecha_nacimiento FROM estudiantes ORDER BY id DESC")
    all_estudiantes = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template('cursos_estudiantes.html', materias=all_materias, cursos=all_cursos, estudiantes=all_estudiantes)

@app.route('/calificaciones', methods=['GET'])
def calificaciones():
    if 'user_id' not in session or session.get('rol') == 'estudiante': 
        return redirect(url_for('login'))
        
    profesor_logueado = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    if session.get('rol') == 'admin':
        cursor.execute("""
            SELECT a.id as asignacion_id, m.nombre_materia, m.semestre, a.seccion 
            FROM asignaciones a
            JOIN materias m ON a.materia_id = m.id
        """)
        mis_asignaciones = cursor.fetchall() 
        
        cursor.execute("""
            SELECT c.id, e.nombre as estudiante_nombre, e.carnet, m.nombre_materia, m.semestre, a.seccion, c.nota, c.estudiante_id, c.asignacion_id
            FROM calificaciones c
            JOIN estudiantes e ON c.estudiante_id = e.id
            JOIN asignaciones a ON c.asignacion_id = a.id
            JOIN materias m ON a.materia_id = m.id
            ORDER BY e.nombre, m.semestre
        """)
    else:
        cursor.execute("""
            SELECT a.id as asignacion_id, m.nombre_materia, m.semestre, a.seccion 
            FROM asignaciones a
            JOIN materias m ON a.materia_id = m.id
            WHERE a.profesor_id = %s
        """, (profesor_logueado,))
        mis_asignaciones = cursor.fetchall()
        
        cursor.execute("""
            SELECT c.id, e.nombre as estudiante_nombre, e.carnet, m.nombre_materia, m.semestre, a.seccion, c.nota, c.estudiante_id, c.asignacion_id
            FROM calificaciones c
            JOIN estudiantes e ON c.estudiante_id = e.id
            JOIN asignaciones a ON c.asignacion_id = a.id
            JOIN materias m ON a.materia_id = m.id
            WHERE a.profesor_id = %s
            ORDER BY e.nombre, m.semestre
        """, (profesor_logueado,))
        
    all_calificaciones = cursor.fetchall()
    
    cursor.execute("SELECT id, nombre, carnet FROM estudiantes ORDER BY nombre")
    lista_alumnos_global = cursor.fetchall()
    
    cursor.close(); conn.close()
    return render_template('calificaciones.html', asignaciones=mis_asignaciones, calificaciones=all_calificaciones, estudiantes_globales=lista_alumnos_global)

# ENDPOINTS REST Transformados Completamaeneto asicnronos 

@app.route('/api/materias/crear', methods=['POST'])
def api_crear_materia():
    if 'user_id' not in session or session.get('rol') == 'estudiante': return jsonify({'error': 'No autorizado'}), 401
    data = request.get_json()
    nombre = data.get('nombre_materia', '').strip()
    semestre_materia = data.get('semestre')
    
    if not nombre or not semestre_materia: return jsonify({'error': 'El nombre y el semestre son requeridos.'}), 400
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO materias (nombre_materia, semestre) VALUES (%s, %s)", (nombre, int(semestre_materia)))
        conn.commit()
        return jsonify({'success': 'Materia guardada exitosamente.'})
    except mysql.connector.Error: return jsonify({'error': 'La materia ya se encuentra registrada.'}), 400
    finally: cursor.close(); conn.close()

@app.route('/api/materias/editar/<int:id>', methods=['POST'])
def api_editar_materia(id):
    if 'user_id' not in session or session.get('rol') != 'admin': return jsonify({'error': 'No autorizado.'}), 401
    data = request.get_json()
    nombre = data.get('nombre_materia', '').strip()
    semestre = data.get('semestre')
    
    if not nombre or not semestre: return jsonify({'error': 'Campos obligatorios incompletos.'}), 400
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("UPDATE materias SET nombre_materia = %s, semestre = %s WHERE id = %s", (nombre, int(semestre), id))
        conn.commit()
        return jsonify({'success': 'Materia actualizada de forma asíncrona.'})
    except mysql.connector.Error: return jsonify({'error': 'El nombre de la materia ingresado ya existe.'}), 400
    finally: cursor.close(); conn.close()

@app.route('/api/materias/eliminar/<int:id>', methods=['DELETE'])
def api_eliminar_materia(id):
    if 'user_id' not in session or session.get('rol') != 'admin': return jsonify({'error': 'No autorizado.'}), 401
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM materias WHERE id = %s", (id,))
        conn.commit()
        return jsonify({'success': 'Materia removida del catálogo de forma segura.'})
    except mysql.connector.Error: return jsonify({'error': 'Imposible eliminar. La materia posee dependencias o registros de notas vigentes.'}), 400
    finally: cursor.close(); conn.close()

@app.route('/api/profesores/crear', methods=['POST'])
def api_crear_profesor():
    if 'user_id' not in session or session.get('rol') != 'admin': return jsonify({'error': 'No autorizado'}), 401
    data = request.get_json()
    nombre = data.get('nombre', '').strip()
    usuario = data.get('usuario', '').strip()
    password = data.get('password', '').strip()
    rol = data.get('rol', 'profesor').strip()
    
    if not nombre or not usuario or not password: return jsonify({'error': 'Datos obligatorios incompletos.'}), 400
    password_hash = generate_password_hash(password)
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO profesores (nombre, usuario, password, rol) VALUES (%s, %s, %s, %s)", (nombre, usuario, password_hash, rol))
        conn.commit()
        return jsonify({'success': 'Cuenta de personal administrativo registrada con éxito.'})
    except mysql.connector.Error: return jsonify({'error': 'El nombre de usuario seleccionado ya existe.'}), 400
    finally: cursor.close(); conn.close()

@app.route('/api/profesores/editar/<int:id>', methods=['POST'])
def api_editar_profesor(id):
    if 'user_id' not in session or session.get('rol') != 'admin': return jsonify({'error': 'No autorizado.'}), 401
    data = request.get_json()
    nombre = data.get('nombre', '').strip()
    usuario = data.get('usuario', '').strip()
    password = data.get('password', '').strip()
    rol = data.get('rol', 'profesor').strip()
    
    if not nombre or not usuario: return jsonify({'error': 'Nombre y usuario requeridos.'}), 400
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        if password:
            password_hash = generate_password_hash(password)
            cursor.execute("UPDATE profesores SET nombre = %s, usuario = %s, password = %s, rol = %s WHERE id = %s", (nombre, usuario, password_hash, rol, id))
        else:
            cursor.execute("UPDATE profesores SET nombre = %s, usuario = %s, rol = %s WHERE id = %s", (nombre, usuario, rol, id))
        conn.commit()
        return jsonify({'success': 'Datos del personal académico actualizados de forma asíncrona.'})
    except mysql.connector.Error: return jsonify({'error': 'El usuario ya se encuentra tomado.'}), 400
    finally: cursor.close(); conn.close()

@app.route('/api/profesores/eliminar/<int:id>', methods=['DELETE'])
def api_eliminar_profesor(id):
    if 'user_id' not in session or session.get('rol') != 'admin': return jsonify({'error': 'No autorizado.'}), 401
    if id == session['user_id']: return jsonify({'error': 'No puedes eliminar tu propia cuenta en sesión.'}), 400
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM profesores WHERE id = %s", (id,))
        conn.commit()
        return jsonify({'success': 'Cuenta de personal revocada exitosamente.'})
    except mysql.connector.Error: return jsonify({'error': 'El docente imparte cursos abiertos con alumnos vinculados.'}), 400
    finally: cursor.close(); conn.close()

@app.route('/api/cursos/crear', methods=['POST'])
def api_crear_curso():
    if 'user_id' not in session or session.get('rol') == 'estudiante': return jsonify({'error': 'No autorizado'}), 401
    profesor_id = session['user_id']
    data = request.get_json()
    materia_id = data.get('materia_id')
    seccion = data.get('seccion', 'A').strip().upper()
    
    if not materia_id or not seccion: return jsonify({'error': 'Datos incompletos.'}), 400
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    
    if session.get('rol') != 'admin':
        cursor.execute("SELECT COUNT(*) as total FROM asignaciones WHERE profesor_id = %s", (profesor_id,))
        if cursor.fetchone()['total'] >= 2:
            cursor.close(); conn.close()
            return jsonify({'error': 'Has alcanzado el límite estricto de 2 asignaciones de la certificación.'}), 400
            
    try:
        cursor.execute("INSERT INTO asignaciones (profesor_id, materia_id, seccion) VALUES (%s, %s, %s)", (profesor_id, materia_id, seccion))
        conn.commit()
        return jsonify({'success': 'Vínculo de curso y sección aperturado con éxito.'})
    except mysql.connector.Error: return jsonify({'error': 'Esta asignatura y sección ya pertenecen a una cátedra activa.'}), 400
    finally: cursor.close(); conn.close()

@app.route('/api/cursos/eliminar/<int:id>', methods=['DELETE'])
def api_eliminar_curso(id):
    if 'user_id' not in session or session.get('rol') == 'estudiante': return jsonify({'error': 'No autorizado'}), 401
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM asignaciones WHERE id = %s", (id,))
        conn.commit()
        return jsonify({'success': 'Curso y sección desvinculados del docente.'})
    except mysql.connector.Error: return jsonify({'error': 'Existen actas de calificaciones vinculadas a este ID de curso.'}), 400
    finally: cursor.close(); conn.close()

@app.route('/api/estudiantes/crear', methods=['POST'])
def api_crear_student():
    if 'user_id' not in session or session.get('rol') == 'estudiante': return jsonify({'error': 'No autorizado'}), 401
    data = request.get_json()
    carnet = data.get('carnet', '').strip()
    nombre = data.get('nombre', '').strip()
    correo = data.get('correo', '').strip()
    telefono = data.get('telefono', '').strip()
    fecha_nacimiento = data.get('fecha_nacimiento', '').strip()
    
    if not nombre: return jsonify({'error': 'El nombre del estudiante es mandatorio.'}), 400
    if not carnet: carnet = f"2026-{random.randint(1000, 9999)}"
        
    password_inicial = generate_password_hash(carnet)
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO estudiantes (carnet, nombre, correo, telefono, fecha_nacimiento, password) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (carnet, nombre, correo if correo else 'Sin Correo', telefono if telefono else None, fecha_nacimiento if fecha_nacimiento else None, password_inicial))
        conn.commit()
        return jsonify({'success': f'Estudiante matriculado. Carné y clave por defecto: {carnet}'})
    except mysql.connector.Error: return jsonify({'error': 'El número de carné ingresado ya existe.'}), 400
    finally: cursor.close(); conn.close()

@app.route('/api/estudiantes/editar/<int:id>', methods=['POST'])
def api_editar_estudiante(id):
    if 'user_id' not in session or session.get('rol') == 'estudiante': return jsonify({'error': 'No autorizado.'}), 401
    data = request.get_json()
    nombre = data.get('nombre', '').strip()
    correo = data.get('correo', '').strip()
    telefono = data.get('telefono', '').strip()
    
    if not nombre: return jsonify({'error': 'El nombre es obligatorio.'}), 400
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE estudiantes SET nombre = %s, correo = %s, telefono = %s WHERE id = %s", (nombre, correo if correo else 'Sin Correo', telefono if telefono else None, id))
    conn.commit(); cursor.close(); conn.close()
    return jsonify({'success': 'Expediente del alumno modificado con éxito.'})

@app.route('/api/estudiantes/eliminar/<int:id>', methods=['DELETE'])
def api_eliminar_estudiante(id):
    if 'user_id' not in session or session.get('rol') == 'estudiante': return jsonify({'error': 'No autorizado.'}), 401
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM estudiantes WHERE id = %s", (id,))
        conn.commit()
        return jsonify({'success': 'Expediente del estudiante eliminado permanentemente.'})
    except mysql.connector.Error: return jsonify({'error': 'No se puede remover el expediente. El alumno posee calificaciones cargadas.'}), 400
    finally: cursor.close(); conn.close()

@app.route('/api/calificaciones/crear', methods=['POST'])
def api_crear_calificacion():
    if 'user_id' not in session or session.get('rol') == 'estudiante': return jsonify({'error': 'No autorizado'}), 401
    data = request.get_json()
    estudiante_id = data.get('estudiante_id')
    asignacion_id = data.get('asignacion_id')
    nota = data.get('nota')
    
    if not estudiante_id or not asignacion_id or nota is None: return jsonify({'error': 'Datos incompletos.'}), 400
    try: nota = int(nota)
    except ValueError: return jsonify({'error': 'La calificación debe ser enteramente numérica.'}), 400
    if nota < 0 or nota > 100: return jsonify({'error': 'Rango de calificación inválido (0-100).'}), 400
    
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    
    # Este paso valida la restriccion de no superar el maximo de 6 asignaturas por alumno
    cursor.execute("SELECT COUNT(*) as total FROM calificaciones WHERE estudiante_id = %s AND asignacion_id != %s", (estudiante_id, asignacion_id))
    if cursor.fetchone()['total'] >= 6:
        cursor.close(); conn.close()
        return jsonify({'error': 'El estudiante ya alcanzó el límite reglamentario de 6 cursos registrados.'}), 400
        
    try:
        cursor.execute("INSERT INTO calificaciones (estudiante_id, asignacion_id, nota) VALUES (%s, %s, %s)", (estudiante_id, asignacion_id, nota))
        conn.commit()
        return jsonify({'success': 'Calificación asentada en el acta de forma exitosa.'})
    except mysql.connector.Error: return jsonify({'error': 'El estudiante ya cuenta con una calificación cargada en este curso.'}), 400
    finally: cursor.close(); conn.close()

@app.route('/api/calificaciones/editar/<int:id>', methods=['POST'])
def api_editar_calificacion(id):
    if 'user_id' not in session or session.get('rol') == 'estudiante': return jsonify({'error': 'No autorizado.'}), 401
    data = request.get_json()
    nota = data.get('nota')
    
    if nota is None: return jsonify({'error': 'Punteo faltante.'}), 400
    try: nota = int(nota)
    except ValueError: return jsonify({'error': 'La nota debe ser entera.'}), 400
    if not (0 <= nota <= 100): return jsonify({'error': 'Punteo fuera de los límites aceptados (0-100).'}), 400
    
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE calificaciones SET nota = %s WHERE id = %s", (nota, id))
    conn.commit(); cursor.close(); conn.close()
    return jsonify({'success': 'Calificación del acta rectificada con éxito.'})

@app.route('/api/calificaciones/eliminar/<int:id>', methods=['DELETE'])
def api_eliminar_calificacion(id):
    if 'user_id' not in session or session.get('rol') == 'estudiante': return jsonify({'error': 'No autorizado.'}), 401
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM calificaciones WHERE id = %s", (id,))
    conn.commit(); cursor.close(); conn.close()
    return jsonify({'success': 'Registro de calificación revocado de forma asíncrona.'})

@app.route('/api/cambiar_password', methods=['POST'])
def api_cambiar_password():
    if 'user_id' not in session: 
        return jsonify({'error': 'No autorizado'}), 401
        
    data = request.get_json()
    pass_actual = data.get('pass_actual')
    pass_nueva = data.get('pass_nueva')
    
    if not pass_actual or not pass_nueva:
        return jsonify({'error': 'Faltan datos obligatorios.'}), 400
        
    user_id = session['user_id']
    rol = session.get('rol')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Detectar la tabla correcta según el rol del usuario en sesión
        tabla = 'estudiantes' if rol == 'estudiante' else 'profesores'
        
        # Obtener el hash actual
        cursor.execute(f"SELECT password FROM {tabla} WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        # Verificar que la contraseña actual ingresada es correcta
        if not user or not check_password_hash(user['password'], pass_actual):
            return jsonify({'error': 'La contraseña actual es incorrecta.'}), 400
            
        # Generar nuevo hash y actualizar
        nuevo_hash = generate_password_hash(pass_nueva)
        cursor.execute(f"UPDATE {tabla} SET password = %s WHERE id = %s", (nuevo_hash, user_id))
        conn.commit()
        
        return jsonify({'success': 'Tu contraseña ha sido actualizada con éxito.'})
        
    except mysql.connector.Error as err:
        return jsonify({'error': 'Hubo un problema al conectar con la base de datos.'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)