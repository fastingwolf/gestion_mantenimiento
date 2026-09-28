import os
from flask import Flask, render_template, request
import psycopg2
from datetime import date
from database import obtener_conexion, inicializar_bd

app = Flask(__name__)

# Intentar inicializar la BD al arrancar (Vercel lo ejecutará en el primer llamado)
try:
    inicializar_bd()
except:
    pass

def consultar_datos_sala(ubicacion_id):
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

@app.route("/")
def index():
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

    if codigo and nombre:
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO equipos (codigo, nombre, categoria, marca, modelo, estado, ubicacion_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (codigo, nombre, categoria, marca, modelo, estado, ubicacion_id))
            conn.commit()
        except psycopg2.IntegrityError:
            pass 
        finally:
            conn.close()

    datos_sala = consultar_datos_sala(ubicacion_id)
    return render_template("partials/sala.html", **datos_sala)

@app.route("/mantenimiento/nuevo", methods=["POST"])
def nuevo_mantenimiento():
    ubicacion_id = int(request.form.get("ubicacion_id"))
    equipo_id = int(request.form.get("equipo_id"))
    tipo = request.form.get("tipo")
    nuevo_estado = request.form.get("nuevo_estado")
    responsable = request.form.get("responsable", "").strip()
    descripcion = request.form.get("descripcion", "").strip()

    if responsable and descripcion:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO mantenimientos (equipo_id, fecha, tipo, descripcion, responsable)
            VALUES (%s, %s, %s, %s, %s)
        """, (equipo_id, str(date.today()), tipo, descripcion, responsable))
        
        cursor.execute("UPDATE equipos SET estado = %s WHERE id = %s", (nuevo_estado, equipo_id))
        conn.commit()
        conn.close()

    datos_sala = consultar_datos_sala(ubicacion_id)
    return render_template("partials/sala.html", **datos_sala)

# Vercel necesita la variable 'app' expuesta (ya la tenemos arriba)
if __name__ == "__main__":
    app.run(debug=True, port=5000)