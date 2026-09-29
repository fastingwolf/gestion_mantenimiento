import os
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from datetime import date
from database import obtener_conexion, inicializar_bd

app = Flask(__name__)
# Necesario para usar 'session' en Flask de forma segura
app.secret_key = os.environ.get("SECRET_KEY", "clave_super_secreta_local")

# Inicializa la BD al arrancar
try:
    inicializar_bd()
except Exception as e:
    print(f"Error en BD: {e}")

def consultar_datos_sala(ubicacion_id):
    """Obtiene los equipos, historial y KPIs de una sala específica."""
    conn = obtener_conexion()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM ubicaciones WHERE id = %s", (ubicacion_id,))
    espacio = cursor.fetchone()

    cursor.execute("SELECT * FROM equipos WHERE ubicacion_id = %s ORDER BY id DESC", (ubicacion_id,))
    equipos = cursor.fetchall()

    cursor.execute("""
        SELECT m.*, e.codigo as equipo_codigo, e.nombre as equipo_nombre 
        FROM mantenimientos m
        INNER JOIN equipos e ON m.equipo_id = e.id
        WHERE e.ubicacion_id = %s
        ORDER BY m.id DESC
    """, (ubicacion_id,))
    historial = cursor.fetchall()
    conn.close()

    total = len(equipos)
    operativos = sum(1 for e in equipos if e["estado"] == "Operativo")
    fallas = total - operativos

    return {
        "espacio": espacio,
        "equipos": equipos,
        "historial": historial,
        "total": total,
        "operativos": operativos,
        "fallas": fallas
    }

# ================= RUTAS DE AUTENTICACIÓN =================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email").strip()
        password = request.form.get("password").strip()
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        usuario = cursor.fetchone()
        conn.close()
        
        if usuario and check_password_hash(usuario["password"], password):
            session["usuario_id"] = usuario["id"]
            session["nombre"] = usuario["nombre"]
            session["rol"] = usuario["rol"]
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Correo o contraseña incorrectos.")
            
    return render_template("login.html")

@app.route("/registro", methods=["POST"])
def registro():
    nombre = request.form.get("nombre").strip()
    email = request.form.get("email").strip()
    password = request.form.get("password").strip()
    rol = request.form.get("rol")
    
    hashed_password = generate_password_hash(password)
    
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO usuarios (nombre, email, password, rol)
            VALUES (%s, %s, %s, %s)
        """, (nombre, email, hashed_password, rol))
        conn.commit()
    except psycopg2.IntegrityError:
        conn.close()
        return render_template("login.html", error="El correo ya está registrado.")
    
    # Iniciar sesión automáticamente después de registrarse
    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
    nuevo_usuario = cursor.fetchone()
    conn.close()
    
    session["usuario_id"] = nuevo_usuario["id"]
    session["nombre"] = nuevo_usuario["nombre"]
    session["rol"] = nuevo_usuario["rol"]
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ================= RUTAS PROTEGIDAS =================

@app.route("/")
def index():
    # Si no hay sesión iniciada, manda al usuario al Login
    if "usuario_id" not in session:
        return redirect(url_for("login"))
        
    conn = obtener_conexion()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM ubicaciones WHERE tipo = 'Laboratorio' ORDER BY nombre ASC")
    laboratorios = cursor.fetchall()

    cursor.execute("SELECT * FROM ubicaciones WHERE tipo = 'Aula' ORDER BY nombre ASC")
    aulas = cursor.fetchall()
    conn.close()

    primer_id = laboratorios[0]["id"] if laboratorios else 1
    datos_sala = consultar_datos_sala(primer_id)

    return render_template(
        "base.html",
        laboratorios=laboratorios,
        aulas=aulas,
        usuario_actual=session, 
        **datos_sala
    )

@app.route("/espacio/<int:ubicacion_id>")
def ver_espacio(ubicacion_id):
    datos_sala = consultar_datos_sala(ubicacion_id)
    return render_template("partials/sala.html", **datos_sala)

@app.route("/equipo/nuevo", methods=["POST"])
def nuevo_equipo():
    ubicacion_id = int(request.form.get("ubicacion_id"))
    codigo = request.form.get("codigo", "").strip()
    nombre = request.form.get("nombre", "").strip()
    categoria = request.form.get("categoria", "")
    marca = request.form.get("marca", "").strip()
    modelo = request.form.get("modelo", "").strip()
    estado = request.form.get("estado", "Operativo")

    mensaje_exito = None
    mensaje_error = None
    tab_activa = "tab-nuevo"

    if codigo and nombre:
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO equipos (codigo, nombre, categoria, marca, modelo, estado, ubicacion_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (codigo, nombre, categoria, marca, modelo, estado, ubicacion_id))
            conn.commit()
            mensaje_exito = f"El equipo '{nombre}' se guardó exitosamente."
            tab_activa = "tab-catalogo" # Si hay éxito, te lleva al catálogo para verlo
        except psycopg2.IntegrityError:
            mensaje_error = f"Error: El código '{codigo}' ya existe. Debe ser único."
        finally:
            conn.close()
    else:
        mensaje_error = "Los campos Código y Nombre son obligatorios."

    datos_sala = consultar_datos_sala(ubicacion_id)
    return render_template("partials/sala.html", 
                           mensaje_exito=mensaje_exito, 
                           mensaje_error=mensaje_error, 
                           tab_activa=tab_activa, 
                           **datos_sala)

@app.route("/mantenimiento/nuevo", methods=["POST"])
def nuevo_mantenimiento():
    ubicacion_id = int(request.form.get("ubicacion_id"))
    equipo_id = request.form.get("equipo_id")
    tipo = request.form.get("tipo")
    nuevo_estado = request.form.get("nuevo_estado")
    responsable = request.form.get("responsable", "").strip()
    descripcion = request.form.get("descripcion", "").strip()

    mensaje_exito = None
    mensaje_error = None
    tab_activa = "tab-mantenimiento"

    if equipo_id and responsable and descripcion:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO mantenimientos (equipo_id, fecha, tipo, descripcion, responsable)
            VALUES (%s, %s, %s, %s, %s)
        """, (equipo_id, str(date.today()), tipo, descripcion, responsable))
        
        cursor.execute("UPDATE equipos SET estado = %s WHERE id = %s", (nuevo_estado, equipo_id))
        conn.commit()
        conn.close()
        
        mensaje_exito = "La orden de servicio fue registrada y el estado actualizado."
        tab_activa = "tab-historial" # Si hay éxito, te muestra el historial
    else:
        mensaje_error = "Por favor completa el responsable y la descripción."

    datos_sala = consultar_datos_sala(ubicacion_id)
    return render_template("partials/sala.html", 
                           mensaje_exito=mensaje_exito, 
                           mensaje_error=mensaje_error, 
                           tab_activa=tab_activa, 
                           **datos_sala)

@app.route("/equipos/eliminar/<int:equipo_id>", methods=["POST"])
def eliminar_equipo(equipo_id):
    # 1. Verificar si el usuario autenticado tiene rol 'admin'
    rol_actual = session.get("rol")
    if not rol_actual and isinstance(session.get("usuario"), dict):
        rol_actual = session.get("usuario", {}).get("rol")

    if rol_actual != "admin":
        return "Acceso denegado: Se requieren permisos de administrador", 403

    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        # 2. Borrar primero los mantenimientos asociados para no violar la Foreign Key
        cursor.execute("DELETE FROM mantenimientos WHERE equipo_id = %s", (equipo_id,))
        # 3. Borrar el equipo
        cursor.execute("DELETE FROM equipos WHERE id = %s", (equipo_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error al eliminar equipo #{equipo_id}: {e}")
    finally:
        conn.close()

    # Redirigir a la vista anterior (la sala actual) o al inicio
    return redirect(request.referrer or url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)

def eliminar_equipo_db(equipo_id: int):
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        # 1. Eliminar mantenimientos asociados para no violar la FK
        cursor.execute("DELETE FROM mantenimientos WHERE equipo_id = %s", (equipo_id,))
        # 2. Eliminar el equipo
        cursor.execute("DELETE FROM equipos WHERE id = %s", (equipo_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error al eliminar equipo: {e}")
        return False
    finally:
        conn.close()