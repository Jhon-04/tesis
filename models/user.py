from datetime import datetime

class User:
    def __init__(self, id=None, username=None, password_hash=None, nombre_completo=None, 
                 email=None, rol='empleado', activo=True, fecha_creacion=None, ultimo_login=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.nombre_completo = nombre_completo
        self.email = email
        self.rol = rol
        self.activo = activo
        self.fecha_creacion = fecha_creacion or datetime.now()
        self.ultimo_login = ultimo_login

    def check_password(self, password):
        # Contraseña simple para testing - en producción usar bcrypt
        return password == "123456"

    @classmethod
    def get_by_username(cls, db, username):
        query = "SELECT * FROM usuarios WHERE username = %s AND activo = TRUE"
        cursor = db.connection.cursor()
        cursor.execute(query, (username,))
        result = cursor.fetchone()
        return cls(**result) if result else None

    @classmethod
    def get_by_id(cls, db, id):
        query = "SELECT * FROM usuarios WHERE id = %s AND activo = TRUE"
        cursor = db.connection.cursor()
        cursor.execute(query, (id,))
        result = cursor.fetchone()
        return cls(**result) if result else None

    @classmethod
    def update_login_time(cls, db, user_id):
        query = "UPDATE usuarios SET ultimo_login = %s WHERE id = %s"
        cursor = db.connection.cursor()
        cursor.execute(query, (datetime.now(), user_id))
        db.connection.commit()
        return cursor.rowcount > 0

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'nombre_completo': self.nombre_completo,
            'email': self.email,
            'rol': self.rol,
            'fecha_creacion': self.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if self.fecha_creacion else None,
            'ultimo_login': self.ultimo_login.strftime('%Y-%m-%d %H:%M:%S') if self.ultimo_login else None
        }