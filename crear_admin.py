from database import obtener_conexion
from werkzeug.security import generate_password_hash

def registrar_admin(nombre, email, password_plana):
    password_hash = generate_password_hash(password_plana)
    conn = obtener_conexion()
    cursor = conn.cursor()

    try:
        # Verificar si el usuario ya existe
        cursor.execute("SELECT id, email, rol FROM usuarios WHERE email = %s", (email,))
        usuario = cursor.fetchone()

        if usuario:
            cursor.execute("""
                UPDATE usuarios 
                SET rol = 'admin', password = %s, nombre = %s 
                WHERE email = %s
            """, (password_hash, nombre, email))
            print(f"El usuario '{email}' ha sido actualizado con rol 'admin'.")
        else:
            cursor.execute("""
                INSERT INTO usuarios (nombre, email, password, rol)
                VALUES (%s, %s, %s, 'admin')
            """, (nombre, email, password_hash))
            print(f"Usuario administrador '{email}' creado exitosamente.")

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error al registrar admin: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    nombre = input("Nombre completo (ej. Administrador): ").strip()
    email = input("Correo electrónico: ").strip().lower()
    password = input("Contraseña: ").strip()

    if email and password:
        registrar_admin(nombre, email, password)
    else:
        print("El correo y la contraseña no pueden estar vacíos.")