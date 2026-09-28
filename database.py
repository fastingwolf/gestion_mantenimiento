import os
import psycopg2
from psycopg2.extras import RealDictCursor

def obtener_conexion():
    """Genera la conexión a PostgreSQL en Neon."""
    # Vercel inyectará automáticamente esta variable de entorno
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("Falta la variable de entorno DATABASE_URL")
    
    # RealDictCursor permite acceder a las columnas por nombre (ej. fila['nombre'])
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

def inicializar_bd():
    """Crea las tablas en PostgreSQL si no existen."""
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()

        # 1. Tabla de Ubicaciones
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ubicaciones (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(255) UNIQUE NOT NULL,
            tipo VARCHAR(50) NOT NULL
        )
        """)

        # 2. Tabla de Equipos
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipos (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(100) UNIQUE NOT NULL,
            nombre VARCHAR(255) NOT NULL,
            categoria VARCHAR(100) NOT NULL,
            marca VARCHAR(100),
            modelo VARCHAR(100),
            estado VARCHAR(50) DEFAULT 'Operativo',
            ubicacion_id INTEGER REFERENCES ubicaciones(id)
        )
        """)

        # 3. Tabla de Bitácora
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS mantenimientos (
            id SERIAL PRIMARY KEY,
            equipo_id INTEGER REFERENCES equipos(id),
            fecha VARCHAR(50) NOT NULL,
            tipo VARCHAR(100) NOT NULL,
            descripcion TEXT NOT NULL,
            responsable VARCHAR(255) NOT NULL,
            estado VARCHAR(50) DEFAULT 'Completado'
        )
        """)

        # 4. Precarga de espacios
        espacios = [
            ("Laboratorio de Aguas", "Laboratorio"),
            ("Laboratorio de Quimica II", "Laboratorio"),
            ("Laboratorio de Instrumental", "Laboratorio"),
            ("Laboratorio de Organica", "Laboratorio"),
            ("Laboratorio de Analitica", "Laboratorio"),
            ("Laboratorio de Procesos Quimicos", "Laboratorio"),
            ("Aula 1", "Aula"),
            ("Aula 2", "Aula"),
            ("Aula 3", "Aula"),
            ("Aula 4", "Aula")
        ]

        # Sintaxis de Postgres para evitar duplicados
        for nombre, tipo in espacios:
            cursor.execute("""
                INSERT INTO ubicaciones (nombre, tipo) 
                VALUES (%s, %s) 
                ON CONFLICT (nombre) DO NOTHING
            """, (nombre, tipo))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error inicializando BD: {e}")

if __name__ == "__main__":
    inicializar_bd()
    print("Base de datos PostgreSQL sincronizada.")