CREATE DATABASE IF NOT EXISTS servicios_navales_bimbo;

USE servicios_navales_bimbo;

CREATE TABLE IF NOT EXISTS documentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    nombre_archivo VARCHAR(255) NOT NULL,
    ruta_archivo VARCHAR(255) NOT NULL,
    estado ENUM('Pagado', 'Pendiente', 'Otro') DEFAULT 'Pendiente',
    fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    observaciones TEXT
);

-- Usuario para la aplicación (ajusta los permisos según necesites)
CREATE USER IF NOT EXISTS 'bimbo_user'@'localhost' IDENTIFIED BY 'bimbo_password';
GRANT ALL PRIVILEGES ON servicios_navales_bimbo.* TO 'bimbo_user'@'localhost';
FLUSH PRIVILEGES;