# 🎓 School U - Sistema de Control Académico Web

![Estado](https://img.shields.io/badge/Estado-Producci%C3%B3n-success)
![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1.3-black?logo=flask)
![MySQL](https://img.shields.io/badge/MySQL-Aiven-4479A1?logo=mysql)
![Render](https://img.shields.io/badge/Deploy-Render-black?logo=render)

School U es una plataforma integral de gestión académica diseñada para administrar docentes, estudiantes, materias y calificaciones. El sistema está construido con un enfoque de alta seguridad, validación estricta de reglas de negocio y un diseño UI/UX responsivo y minimalista.

## 🚀 Enlace en Vivo (Producción)
🌐 **[Haz clic aquí para ver la aplicación en vivo](https://control-academico-yzsg.onrender.com/)**

## ✨ Características Principales
* **Autenticación Basada en Roles (RBAC):** Accesos segmentados para Administradores, Docentes y Estudiantes.
* **Seguridad Criptográfica:** Contraseñas hasheadas mediante algoritmo *scrypt* con validación estricta de longitud.
* **Límites Académicos Inteligentes:**
  * Un docente no puede impartir más de 2 cursos simultáneamente.
  * Un estudiante está limitado a un máximo de 6 cursos por semestre.
* **Consola de Registros Rápidos:** Modales asíncronos para operaciones CRUD sin recarga de página.
* **Renderizado Condicional:** Insignias (badges) dinámicas que evalúan estudiantes Aprobados (≥ 61 pts) y Reprobados (< 61 pts).

## 🛠️ Stack Tecnológico
* **Frontend:** HTML5, Tailwind CSS, JavaScript (Vanilla).
* **Backend:** Python (Flask), Werkzeug (Seguridad).
* **Base de Datos:** MySQL (Clúster en la nube administrado por Aiven.io).
* **Despliegue (DevOps):** Render, Gunicorn (Servidor WSGI).
