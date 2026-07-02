from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector

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

# Login
@app.route('/', methods=['GET', 'POST'])
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

# CRUD Profedores Vista principal y crear
@app.route('/profesores', methods=['GET', 'POST'])
def profesores():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        usuario = request.form['usuario']
        password = request.form['password']
        
        try:
            cursor.execute("INSERT INTO profesores (nombre, usuario, password) VALUES (%s, %s, %s)", (nombre, usuario, password))
            conn.commit()
            flash('Profesor creado exitosamente', 'success')
        except mysql.connector.Error as err:
            flash('Error: El usuario ya existe o los datos son inválidos.', 'error')
            
        return redirect(url_for('profesores'))

    # Obtener la lista de todos los profesores para la tabla
    cursor.execute("SELECT * FROM profesores")
    lista_profesores = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('profesores.html', profesores=lista_profesores)

# Modificar profesor
@app.route('/profesores/editar/<int:id>', methods=['POST'])
def editar_profesor(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    nombre = request.form['nombre'].strip()
    usuario = request.form['usuario'].strip()
    password = request.form['password'].strip()
    
    if not nombre or not usuario or not password:
        flash('Error: No puedes dejar campos vacíos al editar.', 'error')
        return redirect(url_for('profesores'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE profesores 
            SET nombre = %s, usuario = %s, password = %s 
            WHERE id = %s
        """, (nombre, usuario, password, id))
        conn.commit()
        flash('Profesor actualizado correctamente.', 'success')
    except mysql.connector.Error as err:
        flash('Error: El nombre de usuario ya está en uso por otro profesor.', 'error')
        
    cursor.close()
    conn.close()
    return redirect(url_for('profesores'))

# CRUD De Profesores, Eliminar
@app.route('/profesores/eliminar/<int:id>')
def eliminar_profesor(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Impedir que el profesor activo se borre a sí mismo
    if id == session['user_id']:
        flash('No puedes eliminar al usuario con el que tienes sesión activa.', 'error')
        return redirect(url_for('profesores'))

    conn = get_db_connection()
    cursor = conn.connector.cursor() if hasattr(conn, 'connector') else conn.cursor()
    
    try:
        cursor.execute("DELETE FROM profesores WHERE id = %s", (id,))
        conn.commit()
        flash('Profesor eliminado correctamente.', 'success')
    except mysql.connector.Error as err:
        flash('No se puede eliminar el profesor porque tiene cursos asignados.', 'error')
        
    cursor.close()
    conn.close()
    return redirect(url_for('profesores'))

# CRUD Cruso y Estudiantes
@app.route('/cursos_estudiantes', methods=['GET', 'POST'])
def cursos_estudiantes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'crear_curso':
            nombre_curso = request.form['nombre_curso']
            profesor_id = request.form['profesor_id']
            
            cursor.execute("SELECT COUNT(*) as total FROM cursos WHERE profesor_id = %s", (profesor_id,))
            conteo = cursor.fetchone()
            
            if conteo['total'] >= 2:
                flash('Error: Este profesor ya tiene asignado el límite máximo de 2 cursos.', 'error')
            else:
                cursor.execute("INSERT INTO cursos (nombre, profesor_id) VALUES (%s, %s)", (nombre_curso, profesor_id))
                conn.commit()
                flash('Curso creado y asignado exitosamente', 'success')
                
        elif action == 'crear_estudiante':
            nombre_estudiante = request.form['nombre_estudiante']
            cursor.execute("INSERT INTO estudiantes (nombre) VALUES (%s)", (nombre_estudiante,))
            conn.commit()
            flash('Estudiante registrado exitosamente', 'success')
            
        return redirect(url_for('cursos_estudiantes'))

    cursor.execute("SELECT * FROM profesores")
    all_profesores = cursor.fetchall()
    
    cursor.execute("""
        SELECT c.id, c.nombre as curso_nombre, p.nombre as profesor_nombre 
        FROM cursos c 
        LEFT JOIN profesores p ON c.profesor_id = p.id
    """)
    all_cursos = cursor.fetchall()
    
    cursor.execute("SELECT * FROM estudiantes")
    all_estudiantes = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('cursos_estudiantes.html', profesores=all_profesores, cursos=all_cursos, estudiantes=all_estudiantes)

# Modificar curso
@app.route('/cursos/editar/<int:id>', methods=['POST'])
def editar_curso(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    nombre = request.form['nombre_curso'].strip()
    if not nombre: return redirect(url_for('cursos_estudiantes'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE cursos SET nombre = %s WHERE id = %s", (nombre, id))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Curso actualizado correctamente.', 'success')
    return redirect(url_for('cursos_estudiantes'))

# Modificar estudiante
@app.route('/estudiantes/editar/<int:id>', methods=['POST'])
def editar_estudiante(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    nombre = request.form['nombre_estudiante'].strip()
    if not nombre: return redirect(url_for('cursos_estudiantes'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE estudiantes SET nombre = %s WHERE id = %s", (nombre, id))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Estudiante actualizado correctamente.', 'success')
    return redirect(url_for('cursos_estudiantes'))

# Eliminar Curso
@app.route('/cursos/eliminar/<int:id>')
def eliminar_curso(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cursos WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Curso eliminado correctamente', 'success')
    return redirect(url_for('cursos_estudiantes'))

# Eliminar Estudiante
@app.route('/estudiantes/eliminar/<int:id>')
def eliminar_estudiante(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM estudiantes WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Estudiante eliminado correctamente', 'success')
    return redirect(url_for('cursos_estudiantes'))

# CRUD Calificaciones
@app.route('/calificaciones', methods=['GET', 'POST'])
def calificaciones():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        estudiante_id = request.form['estudiante_id']
        curso_id = request.form['curso_id']
        semestre = request.form['semestre']
        nota = request.form['nota']
        
        cursor.execute("""
            SELECT COUNT(DISTINCT curso_id) as total_cursos 
            FROM calificaciones 
            WHERE estudiante_id = %s AND curso_id != %s
        """, (estudiante_id, curso_id))
        conteo_cursos = cursor.fetchone()
        
        cursor.execute("""
            SELECT id FROM calificaciones 
            WHERE estudiante_id = %s AND curso_id = %s AND semestre = %s
        """, (estudiante_id, curso_id, semestre))
        nota_existente = cursor.fetchone()
        
        if conteo_cursos['total_cursos'] >= 6:
            flash('Error: El estudiante ya alcanzó el límite máximo de 6 cursos asignados.', 'error')
        elif nota_existente:
            flash('Error: Ya existe una calificación registrada para este estudiante en este curso and semestre.', 'error')
        else:
            cursor.execute("""
                INSERT INTO calificaciones (estudiante_id, curso_id, semestre, nota) 
                VALUES (%s, %s, %s, %s)
            """, (estudiante_id, curso_id, semestre, nota))
            conn.commit()
            flash('Calificación registrada exitosamente.', 'success')
            
        return redirect(url_for('calificaciones'))

    cursor.execute("SELECT * FROM estudiantes")
    all_estudiantes = cursor.fetchall()
    
    cursor.execute("SELECT * FROM cursos")
    all_cursos = cursor.fetchall()
    
    cursor.execute("""
        SELECT c.id, e.nombre as estudiante_nombre, cr.nombre as curso_nombre, c.semestre, c.nota 
        FROM calificaciones c
        JOIN estudiantes e ON c.estudiante_id = e.id
        JOIN cursos cr ON c.curso_id = cr.id
        ORDER BY e.nombre, c.semestre
    """)
    all_calificaciones = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('calificaciones.html', estudiantes=all_estudiantes, cursos=all_cursos, calificaciones=all_calificaciones)
# Modificar calificacion
@app.route('/calificaciones/editar/<int:id>', methods=['POST'])
def editar_calificacion(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    try:
        nota = int(request.form['nota'])
    except ValueError:
        flash('Error: La calificación debe ser un número entero.', 'error')
        return redirect(url_for('calificaciones'))
        
    if nota < 0 or nota > 100:
        flash('Error: La calificación debe estar entre 0 y 100.', 'error')
        return redirect(url_for('calificaciones'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE calificaciones SET nota = %s WHERE id = %s", (nota, id))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Calificación actualizada correctamente.', 'success')
    return redirect(url_for('calificaciones'))

# Eliminar calificacion
@app.route('/calificaciones/eliminar/<int:id>')
def eliminar_calificacion(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM calificaciones WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Registro de calificación eliminado.', 'success')
    return redirect(url_for('calificaciones'))

# --- LOGOUT ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)