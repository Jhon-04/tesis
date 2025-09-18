from datetime import datetime

class Document:
    def __init__(self, id=None, nombre=None, descripcion=None, nombre_archivo=None, 
                 ruta_archivo=None, estado=None, fecha_subida=None, 
                 fecha_actualizacion=None, observaciones=None, usuario_id=None, usuario_nombre=None):
        self.id = id
        self.nombre = nombre
        self.descripcion = descripcion
        self.nombre_archivo = nombre_archivo
        self.ruta_archivo = ruta_archivo
        self.estado = estado
        self.fecha_subida = fecha_subida or datetime.now()
        self.fecha_actualizacion = fecha_actualizacion or datetime.now()
        self.observaciones = observaciones
        self.usuario_id = usuario_id
        self.usuario_nombre = usuario_nombre

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'nombre_archivo': self.nombre_archivo,
            'estado': self.estado,
            'fecha_subida': self.fecha_subida.strftime('%Y-%m-%d %H:%M:%S') if self.fecha_subida else None,
            'observaciones': self.observaciones,
            'usuario_nombre': self.usuario_nombre
        }

    @classmethod
    def create(cls, db, document):
        query = """
        INSERT INTO documentos (nombre, descripcion, nombre_archivo, ruta_archivo, estado, observaciones, usuario_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (document.nombre, document.descripcion, document.nombre_archivo, 
                 document.ruta_archivo, document.estado, document.observaciones, document.usuario_id)
        
        cursor = db.connection.cursor()
        cursor.execute(query, params)
        db.connection.commit()
        document.id = cursor.lastrowid
        return document

    @classmethod
    def get_all(cls, db):
        query = """
        SELECT d.*, u.nombre_completo as usuario_nombre 
        FROM documentos d 
        LEFT JOIN usuarios u ON d.usuario_id = u.id 
        ORDER BY d.fecha_actualizacion DESC
        """
        cursor = db.connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        return [cls(**row) for row in results] if results else []

    @classmethod
    def get_by_id(cls, db, id):
        query = """
        SELECT d.*, u.nombre_completo as usuario_nombre 
        FROM documentos d 
        LEFT JOIN usuarios u ON d.usuario_id = u.id 
        WHERE d.id = %s
        """
        cursor = db.connection.cursor()
        cursor.execute(query, (id,))
        result = cursor.fetchone()
        return cls(**result) if result else None

    @classmethod
    def search(cls, db, search_term, search_type='todo'):
        base_query = """
        SELECT d.*, u.nombre_completo as usuario_nombre 
        FROM documentos d 
        LEFT JOIN usuarios u ON d.usuario_id = u.id 
        WHERE 
        """
        
        if search_type == 'id':
            query = base_query + "d.id LIKE %s"
        elif search_type == 'nombre':
            query = base_query + "d.nombre LIKE %s"
        elif search_type == 'estado':
            query = base_query + "d.estado LIKE %s"
        elif search_type == 'usuario':
            query = base_query + "u.nombre_completo LIKE %s"
        else:  # buscar en todo
            query = base_query + "(d.nombre LIKE %s OR d.descripcion LIKE %s OR d.observaciones LIKE %s OR u.nombre_completo LIKE %s)"
        
        search_pattern = f"%{search_term}%"
        
        cursor = db.connection.cursor()
        if search_type == 'todo':
            cursor.execute(query, (search_pattern, search_pattern, search_pattern, search_pattern))
        else:
            cursor.execute(query, (search_pattern,))
        
        results = cursor.fetchall()
        return [cls(**row) for row in results] if results else []

    @classmethod
    def search_by_date(cls, db, fecha_inicio, fecha_fin):
        query = """
        SELECT d.*, u.nombre_completo as usuario_nombre 
        FROM documentos d 
        LEFT JOIN usuarios u ON d.usuario_id = u.id 
        WHERE DATE(d.fecha_subida) BETWEEN %s AND %s
        ORDER BY d.fecha_subida DESC
        """
        
        cursor = db.connection.cursor()
        cursor.execute(query, (fecha_inicio, fecha_fin))
        results = cursor.fetchall()
        return [cls(**row) for row in results] if results else []

    @classmethod
    def update(cls, db, document):
        query = """
        UPDATE documentos 
        SET nombre = %s, descripcion = %s, estado = %s, observaciones = %s
        WHERE id = %s
        """
        params = (document.nombre, document.descripcion, document.estado, 
                 document.observaciones, document.id)
        
        cursor = db.connection.cursor()
        cursor.execute(query, params)
        db.connection.commit()
        return document

    @classmethod
    def delete(cls, db, id):
        query = "DELETE FROM documentos WHERE id = %s"
        cursor = db.connection.cursor()
        cursor.execute(query, (id,))
        db.connection.commit()
        return cursor.rowcount > 0