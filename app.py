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

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Buscar profesor en la BD
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

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# CRUD Curso y estudiantes
@app.route('/cursos_estudiantes', methods=['GET', 'POST'])
def cursos_estudiantes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        # Logica para crear curso
        if action == 'crear_curso':
            nombre_curso = request.form['nombre_curso']
            profesor_id = request.form['profesor_id']
            
            # Validación Backend, contar cuántos cursos tiene ya ese profesor
            cursor.execute("SELECT COUNT(*) as total FROM cursos WHERE profesor_id = %s", (profesor_id,))
            conteo = cursor.fetchone()
            
            if conteo['total'] >= 2:
                flash('Error: Este profesor ya tiene asignado el límite máximo de 2 cursos.', 'error')
            else:
                cursor.execute("INSERT INTO cursos (nombre, profesor_id) VALUES (%s, %s)", (nombre_curso, profesor_id))
                conn.commit()
                flash('Curso creado y asignado exitosamente', 'success')
                
        # Logica para crear Estudiante
        elif action == 'crear_estudiante':
            nombre_estudiante = request.form['nombre_estudiante']
            cursor.execute("INSERT INTO estudiantes (nombre) VALUES (%s)", (nombre_estudiante,))
            conn.commit()
            flash('Estudiante registrado exitosamente', 'success')
            
        return redirect(url_for('cursos_estudiantes'))

    # Obtener datos para renderizar la pantalla
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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

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
        
        # Validar que el estudiante no tenga ya 6 cursos distintos
        cursor.execute("""
            SELECT COUNT(DISTINCT curso_id) as total_cursos 
            FROM calificaciones 
            WHERE estudiante_id = %s AND curso_id != %s
        """, (estudiante_id, curso_id))
        conteo_cursos = cursor.fetchone()
        
        # Verificar si ya existe una nota para este curso en este semestre
        cursor.execute("""
            SELECT id FROM calificaciones 
            WHERE estudiante_id = %s AND curso_id = %s AND semestre = %s
        """, (estudiante_id, curso_id, semestre))
        nota_existente = cursor.fetchone()
        
        if conteo_cursos['total_cursos'] >= 6:
            flash('Error: El estudiante ya alcanzó el límite máximo de 6 cursos asignados.', 'error')
        elif nota_existente:
            flash('Error: Ya existe una calificación registrada para este estudiante en este curso y semestre.', 'error')
        else:
            # Insertar la calificación si pasa los filtros
            cursor.execute("""
                INSERT INTO calificaciones (estudiante_id, curso_id, semestre, nota) 
                VALUES (%s, %s, %s, %s)
            """, (estudiante_id, curso_id, semestre, nota))
            conn.commit()
            flash('Calificación registrada exitosamente.', 'success')
            
        return redirect(url_for('calificaciones'))

    # Obtener catálogos para los selects del formulario
    cursor.execute("SELECT * FROM estudiantes")
    all_estudiantes = cursor.fetchall()
    
    cursor.execute("SELECT * FROM cursos")
    all_cursos = cursor.fetchall()
    
    # Obtener el listado de todas las calificaciones para la tabla
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

# Eliminar Calificacion
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
if __name__ == '__main__':
    app.run(debug=True, port=5000)    