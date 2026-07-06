from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
import mysql.connector
import random

app = Flask(__name__)
app.secret_key = 'clave_secreta_certificacion'

# Configuración de la conexión a MySQL en XAMPP
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="control_colegio"
    )

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('colegio.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM profesores WHERE usuario = %s AND password = %s", (usuario, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['nombre']
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            return redirect(url_for('login'))
            
    return render_template('login.html')

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- VISTAS PRINCIPALES DEL PANEL ADMINISTRATIVO (HTML) ---

@app.route('/profesores', methods=['GET'])
def profesores():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nombre, usuario, password FROM profesores ORDER BY id DESC")
    lista_profesores = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template('profesores.html', profesores=lista_profesores)

@app.route('/cursos_estudiantes', methods=['GET'])
def cursos_estudiantes():
    if 'user_id' not in session: return redirect(url_for('login'))
    profesor_logueado = session['user_id']
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT id, nombre_grado, seccion FROM grados ORDER BY nombre_grado, seccion")
    all_grados = cursor.fetchall()
    
    cursor.execute("SELECT id, nombre_materia FROM materias ORDER BY nombre_materia")
    all_materias = cursor.fetchall()
    
    cursor.execute("""
        SELECT a.id, m.nombre_materia as curso_nombre, g.nombre_grado, g.seccion 
        FROM asignaciones a
        JOIN materias m ON a.materia_id = m.id
        JOIN grados g ON a.grado_id = g.id
        WHERE a.profesor_id = %s
        ORDER BY g.nombre_grado, m.nombre_materia
    """, (profesor_logueado,))
    all_cursos = cursor.fetchall()
    
    cursor.execute("""
        SELECT e.id, e.carnet, e.nombre, e.correo, e.telefono, e.fecha_nacimiento, g.nombre_grado, g.seccion, e.grado_id
        FROM estudiantes e
        JOIN grados g ON e.grado_id = g.id
        ORDER BY e.id DESC
    """)
    all_estudiantes = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template('cursos_estudiantes.html', grados=all_grados, materias=all_materias, cursos=all_cursos, estudiantes=all_estudiantes)

@app.route('/calificaciones', methods=['GET'])
def calificaciones():
    if 'user_id' not in session: return redirect(url_for('login'))
    profesor_logueado = session['user_id']
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT a.id as asignacion_id, m.nombre_materia, g.nombre_grado, g.seccion 
        FROM asignaciones a
        JOIN materias m ON a.materia_id = m.id
        JOIN grados g ON a.grado_id = g.id
        WHERE a.profesor_id = %s
    """, (profesor_logueado,))
    mis_asignaciones = cursor.fetchall()
    
    cursor.execute("""
        SELECT c.id, e.nombre as estudiante_nombre, e.carnet, m.nombre_materia, g.nombre_grado, g.seccion, c.semestre, c.nota, c.estudiante_id, c.asignacion_id
        FROM calificaciones c
        JOIN estudiantes e ON c.estudiante_id = e.id
        JOIN asignaciones a ON c.asignacion_id = a.id
        JOIN materias m ON a.materia_id = m.id
        JOIN grados g ON a.grado_id = g.id
        WHERE a.profesor_id = %s
        ORDER BY e.nombre, c.semestre
    """, (profesor_logueado,))
    all_calificaciones = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template('calificaciones.html', asignaciones=mis_asignaciones, calificaciones=all_calificaciones)

# --- ENDPOINTS DE LA API REST (JSON ASÍNCRONOS) ---

@app.route('/api/materias/crear', methods=['POST'])
def api_crear_materia():
    if 'user_id' not in session: return jsonify({'error': 'no autorizado'}), 401
    data = request.get_json()
    nombre = data.get('nombre_materia', '').strip()
    if not nombre: return jsonify({'error': 'el nombre de la materia es requerido.'}), 400
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO materias (nombre_materia) VALUES (%s)", (nombre,))
        conn.commit()
        return jsonify({'success': 'materia guardada exitosamente.'})
    except mysql.connector.Error: return jsonify({'error': 'la materia ya se encuentra registrada.'}), 400
    finally: cursor.close(); conn.close()

@app.route('/api/grados/crear', methods=['POST'])
def api_crear_grado():
    if 'user_id' not in session: return jsonify({'error': 'no autorizado'}), 401
    data = request.get_json()
    nombre = data.get('nombre_grado', '').strip()
    seccion = data.get('seccion', '').strip().upper()
    if not nombre or not seccion: return jsonify({'error': 'nombre y seccion requeridos.'}), 400
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO grados (nombre_grado, seccion) VALUES (%s, %s)", (nombre, seccion))
        conn.commit()
        return jsonify({'success': 'grado y seccion creados con exito.'})
    except mysql.connector.Error: return jsonify({'error': 'esta seccion de grado ya existe.'}), 400
    finally: cursor.close(); conn.close()

@app.route('/api/profesores/crear', methods=['POST'])
def api_crear_profesor():
    if 'user_id' not in session: return jsonify({'error': 'no autorizado'}), 401
    data = request.get_json()
    nombre, usuario, password = data.get('nombre', '').strip(), data.get('usuario', '').strip(), data.get('password', '').strip()
    if not nombre or not usuario or not password: return jsonify({'error': 'datos incompletos.'}), 400
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO profesores (nombre, usuario, password) VALUES (%s, %s, %s)", (nombre, usuario, password))
        conn.commit()
        return jsonify({'success': 'profesor creado exitosamente'})
    except mysql.connector.Error: return jsonify({'error': 'el usuario ya existe.'}), 400
    finally: cursor.close(); conn.close()

@app.route('/api/cursos/crear', methods=['POST'])
def api_crear_curso():
    if 'user_id' not in session: return jsonify({'error': 'no autorizado'}), 401
    profesor_id = session['user_id']
    data = request.get_json()
    materia_id, grado_id = data.get('materia_id'), data.get('grado_id')
    if not materia_id or not grado_id: return jsonify({'error': 'datos incompletos.'}), 400
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) as total FROM asignaciones WHERE profesor_id = %s", (profesor_id,))
    if cursor.fetchone()['total'] >= 2:
        cursor.close(); conn.close()
        return jsonify({'error': 'has alcanzado el limite maximo de 2 cursos.'}), 400
    try:
        cursor.execute("INSERT INTO asignaciones (profesor_id, materia_id, grado_id) VALUES (%s, %s, %s)", (profesor_id, materia_id, grado_id))
        conn.commit()
        return jsonify({'success': 'curso asignado exitosamente'})
    except mysql.connector.Error: return jsonify({'error': 'esta asignacion ya pertenece a un catedratico.'}), 400
    finally: cursor.close(); conn.close()

@app.route('/api/estudiantes/crear', methods=['POST'])
def api_crear_student():
    if 'user_id' not in session: return jsonify({'error': 'no authorized'}), 401
    data = request.get_json()
    carnet = data.get('carnet', '').strip()
    nombre = data.get('nombre', '').strip()
    correo = data.get('correo', '').strip()
    telefono = data.get('telefono', '').strip()
    fecha_nacimiento = data.get('fecha_nacimiento', '').strip()
    grado_id = data.get('grado_id')
    
    if not nombre or not grado_id:
        return jsonify({'error': 'el nombre y el grado son campos obligatorios.'}), 400
        
    if not carnet:
        carnet = f"2026-{random.randint(1000, 9999)}"
        
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO estudiantes (carnet, nombre, correo, telefono, fecha_nacimiento, grado_id) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (carnet, nombre, correo if correo else 'Sin Correo', telefono if telefono else None, fecha_nacimiento if fecha_nacimiento else None, grado_id))
        conn.commit()
        return jsonify({'success': f'estudiante matriculado exitosamente con el carnet: {carnet}'})
    except mysql.connector.Error: return jsonify({'error': 'el numero de carnet ya se encuentra registrado.'}), 400
    finally: cursor.close(); conn.close()

@app.route('/api/asignaciones/<int:id>/estudiantes', methods=['GET'])
def api_estudiantes_por_asignacion(id):
    if 'user_id' not in session: return jsonify({'error': 'no autorizado'}), 401
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT grado_id FROM asignaciones WHERE id = %s", (id,))
    asig = cursor.fetchone()
    if not asig: cursor.close(); conn.close(); return jsonify([])
    cursor.execute("SELECT id, nombre, carnet FROM estudiantes WHERE grado_id = %s ORDER BY nombre", (asig['grado_id'],))
    estudiantes = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(estudiantes)

@app.route('/api/calificaciones/crear', methods=['POST'])
def api_crear_calificacion():
    if 'user_id' not in session: return jsonify({'error': 'no autorizado'}), 401
    data = request.get_json()
    estudiante_id, asignacion_id, semestre, nota = data.get('estudiante_id'), data.get('asignacion_id'), data.get('semestre'), data.get('nota')
    if not estudiante_id or not asignacion_id or not semestre or nota is None: return jsonify({'error': 'datos incompletos'}), 400
    try: nota = int(nota)
    except ValueError: return jsonify({'error': 'la nota debe ser numerica.'}), 400
    if nota < 0 or nota > 100: return jsonify({'error': 'rango de nota invalido (0-100).'}), 400
    
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(DISTINCT asignacion_id) as total FROM calificaciones WHERE estudiante_id = %s AND asignacion_id != %s", (estudiante_id, asignacion_id))
    if cursor.fetchone()['total'] >= 6:
        cursor.close(); conn.close()
        return jsonify({'error': 'el estudiante ya alcanzo el limite de 6 cursos registrados.'}), 400
    cursor.execute("SELECT id FROM calificaciones WHERE estudiante_id = %s AND asignacion_id = %s AND semestre = %s", (estudiante_id, asignacion_id, semestre))
    if cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'ya existe calificacion en este semestre.'}), 400
    cursor.execute("INSERT INTO calificaciones (estudiante_id, asignacion_id, semestre, nota) VALUES (%s, %s, %s, %s)", (estudiante_id, asignacion_id, semestre, nota))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'success': 'calificacion asentada de forma asincrona.'})

# --- ENDPOINTS TRADICIONALES DE MODIFICACIÓN Y ELIMINACIÓN ---

@app.route('/profesores/editar/<int:id>', methods=['POST'])
def editar_profesor(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    nombre, usuario, password = request.form['nombre'].strip(), request.form['usuario'].strip(), request.form['password'].strip()
    conn = get_db_connection(); cursor = conn.cursor()
    try:
        cursor.execute("UPDATE profesores SET nombre = %s, usuario = %s, password = %s WHERE id = %s", (nombre, usuario, password, id))
        conn.commit()
    except mysql.connector.Error: flash('Error: Usuario ya existente.', 'error')
    cursor.close(); conn.close()
    return redirect(url_for('profesores'))

@app.route('/estudiantes/editar/<int:id>', methods=['POST'])
def editar_estudiante(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    nombre = request.form['nombre_estudiante'].strip()
    correo = request.form['correo_estudiante'].strip()
    telefono = request.form['telefono_estudiante'].strip()
    grado_id = request.form['grado_id']
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("""
        UPDATE estudiantes 
        SET nombre = %s, correo = %s, telefono = %s, grado_id = %s 
        WHERE id = %s
    """, (nombre, correo if correo else 'Sin Correo', telefono if telefono else None, grado_id, id))
    conn.commit(); cursor.close(); conn.close()
    return redirect(url_for('cursos_estudiantes'))

@app.route('/profesores/eliminar/<int:id>')
def eliminar_profesor(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    if id == session['user_id']: return redirect(url_for('profesores'))
    conn = get_db_connection(); cursor = conn.cursor()
    try: cursor.execute("DELETE FROM profesores WHERE id = %s", (id,)); conn.commit()
    except mysql.connector.Error: flash('Error: El profesor imparte materias activas.', 'error')
    cursor.close(); conn.close()
    return redirect(url_for('profesores'))

@app.route('/cursos/eliminar/<int:id>')
def eliminar_curso(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM asignaciones WHERE id = %s", (id,)); conn.commit()
    cursor.close(); conn.close()
    return redirect(url_for('cursos_estudiantes'))

@app.route('/estudiantes/eliminar/<int:id>')
def eliminar_estudiante(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM estudiantes WHERE id = %s", (id,)); conn.commit()
    cursor.close(); conn.close()
    return redirect(url_for('cursos_estudiantes'))

@app.route('/calificaciones/editar/<int:id>', methods=['POST'])
def editar_calificacion(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    try:
        nota = int(request.form['nota'])
        if 0 <= nota <= 100:
            conn = get_db_connection(); cursor = conn.cursor()
            cursor.execute("UPDATE calificaciones SET nota = %s WHERE id = %s", (nota, id)); conn.commit()
            cursor.close(); conn.close()
    except ValueError: pass
    return redirect(url_for('calificaciones'))

@app.route('/calificaciones/eliminar/<int:id>')
def eliminar_calificacion(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM calificaciones WHERE id = %s", (id,)); conn.commit()
    cursor.close(); conn.close()
    return redirect(url_for('calificaciones'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)