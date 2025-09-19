from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, session, make_response
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from database.db_connection import configure_db
from models.document import Document as DocumentModel
from models.user import User
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus.flowables import KeepTogether
import io
import time

app = Flask(__name__)
app.secret_key = '20541651889-bimbo-secret-key-advanced'

# Configuración de la base de datos
mysql = configure_db(app)

# Configuración de uploads
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB máximo
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Lista de embarcaciones
EMBARCACIONES = [
    "ALEJANDRIA I", "ALEJANDRIA II", "ALEJANDRIA III", "ALEJANDRIA VI",
    "ANDES 31", "ANDES 32", "ANDES 52", "ANDES 53", "ANDREA", "BRUNELLA II",
    "BRYAN", "C&Z 8", "CHIMBOTE 1", "COMANCHE II", "COMANCHE III", "COMANCHE V",
    "CRISTINA", "DALMACIA", "DON MOISES", "ELISA", "GALILEO", "GRUNEPA 3",
    "INCAMAR 1", "INCAMAR 2", "INCAMAR 3", "JADRAN I", "JADRAN II", "JUANITA",
    "MARFIL", "MARU", "MATTY", "PIZARRO 9", "RIBAR I", "RIBAR III", "RIBAR VI",
    "RIBAR IX", "RIBAR XIII", "RIBAR XIV", "RIBAR XV", "RIBAR XVI", "RIBAR XVIII",
    "RICARDO", "RODGA 1", "SAN FERNANDO", "SIMY 1", "SIMY 2", "SIMY 3", "SIMY 4",
    "SIMY 7", "TALARA 1", "TAMBO 1", "YOVANA", "WESTELLA", "REM ANDES 01", "REM INCA 01"
]

# Estados de seguimiento
ESTADOS_SEGUIMIENTO = [
    "SE ENVIÓ PRESUPUESTO",
    "TIENE ORDEN DE COMPRA",
    "SE ENVIÓ CONFORMIDAD",
    "TIENE HES PARA FACTURAR",
    "SE FACTURÓ",
    "PAGADO"
]

# Tipos de búsqueda
TIPOS_BUSQUEDA = [
    {'value': 'todo', 'label': 'Buscar en todo'},
    {'value': 'id', 'label': 'Por ID'},
    {'value': 'nombre', 'label': 'Por embarcación'},
    {'value': 'estado', 'label': 'Por estado'},
    {'value': 'usuario', 'label': 'Por usuario'},
    {'value': 'fecha', 'label': 'Por fecha'}
]

# Cache para resultados de búsqueda
search_cache = {}
CACHE_TIMEOUT = 300  # 5 minutos

# Context processor para inyectar variables globales
@app.context_processor
def inject_global_vars():
    user_data = None
    if 'user_id' in session:
        user = User.get_by_id(mysql, session['user_id'])
        if user:
            user_data = user.to_dict()
    
    return {
        'now': datetime.now(),
        'embarcaciones': EMBARCACIONES,
        'estados_seguimiento': ESTADOS_SEGUIMIENTO,
        'tipos_busqueda': TIPOS_BUSQUEDA,
        'current_user': user_data
    }

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor inicia sesión para acceder a esta página', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_cached_search(key):
    """Obtiene resultados de búsqueda desde la cache"""
    if key in search_cache:
        cached_data = search_cache[key]
        if time.time() - cached_data['timestamp'] < CACHE_TIMEOUT:
            return cached_data['data']
    return None

def set_cached_search(key, data):
    """Guarda resultados de búsqueda en la cache"""
    search_cache[key] = {
        'data': data,
        'timestamp': time.time()
    }

@app.route('/')
@login_required
def index():
    return redirect(url_for('list_documents'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.get_by_username(mysql, username)
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.rol
            
            User.update_login_time(mysql, user.id)
            flash(f'Bienvenido {user.nombre_completo}!', 'success')
            return redirect(url_for('list_documents'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('login'))

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_document():
    if request.method == 'POST':
        if 'documento' not in request.files:
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        file = request.files['documento']
        
        if file.filename == '':
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                
                file.save(filepath)
                
                nombre_embarcacion = request.form.get('nombre_embarcacion', '')
                if nombre_embarcacion == 'otro':
                    nombre_embarcacion = request.form.get('otra_embarcacion', '')
                
                document = DocumentModel(
                    nombre=nombre_embarcacion,
                    descripcion=request.form.get('descripcion', ''),
                    nombre_archivo=filename,
                    ruta_archivo=unique_filename,
                    estado=request.form.get('estado', ESTADOS_SEGUIMIENTO[0]),
                    observaciones=request.form.get('observaciones', ''),
                    usuario_id=session['user_id']
                )
                
                DocumentModel.create(mysql, document)
                
                # Limpiar cache después de subir nuevo documento
                global search_cache
                search_cache = {}
                
                flash('Documento subido exitosamente!', 'success')
                return redirect(url_for('list_documents'))
            
            except Exception as e:
                flash(f'Error al subir el documento: {str(e)}', 'danger')
                return redirect(request.url)
        
        flash('Solo se permiten archivos PDF, JPG, JPEG y PNG', 'danger')
    
    return render_template('upload.html')

@app.route('/documents')
@login_required
def list_documents():
    query = request.args.get('q', '').strip()
    search_type = request.args.get('search_type', 'todo')
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    
    # Generar clave única para la cache
    cache_key = f"{search_type}:{query}:{fecha_inicio}:{fecha_fin}"
    
    # Intentar obtener de cache primero
    cached_documents = get_cached_search(cache_key)
    
    if cached_documents is not None:
        documents = cached_documents
    else:
        # Búsqueda en base de datos
        if search_type == 'fecha' and fecha_inicio and fecha_fin:
            documents = DocumentModel.search_by_date(mysql, fecha_inicio, fecha_fin)
        elif query:
            documents = DocumentModel.search(mysql, query, search_type)
        else:
            documents = DocumentModel.get_all(mysql)
        
        # Guardar en cache
        set_cached_search(cache_key, documents)
    
    return render_template('documents.html', 
                         documents=documents, 
                         search_query=query, 
                         search_type=search_type,
                         fecha_inicio=fecha_inicio,
                         fecha_fin=fecha_fin)

@app.route('/api/documents')
@login_required
def api_documents():
    query = request.args.get('q', '').strip()
    search_type = request.args.get('search_type', 'todo')
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    
    # Generar clave única para la cache
    cache_key = f"api:{search_type}:{query}:{fecha_inicio}:{fecha_fin}"
    
    # Intentar obtener de cache primero
    cached_documents = get_cached_search(cache_key)
    
    if cached_documents is not None:
        documents = cached_documents
    else:
        # Búsqueda en base de datos
        if search_type == 'fecha' and fecha_inicio and fecha_fin:
            documents = DocumentModel.search_by_date(mysql, fecha_inicio, fecha_fin)
        elif query:
            documents = DocumentModel.search(mysql, query, search_type)
        else:
            documents = DocumentModel.get_all(mysql)
        
        # Guardar en cache
        set_cached_search(cache_key, documents)
    
    # Asegurarse de que todos los documentos tengan usuario_nombre
    for doc in documents:
        if not hasattr(doc, 'usuario_nombre') or doc.usuario_nombre is None:
            doc.usuario_nombre = "Usuario Desconocido"
    
    return jsonify([doc.to_dict() for doc in documents])

@app.route('/document/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_document(id):
    document = DocumentModel.get_by_id(mysql, id)
    
    if not document:
        flash('Documento no encontrado', 'danger')
        return redirect(url_for('list_documents'))
    
    if request.method == 'POST':
        nombre_embarcacion = request.form.get('nombre_embarcacion', '')
        if nombre_embarcacion == 'otro':
            nombre_embarcacion = request.form.get('otra_embarcacion', '')
        
        document.nombre = nombre_embarcacion
        document.descripcion = request.form.get('descripcion', document.descripcion)
        document.estado = request.form.get('estado', document.estado)
        document.observaciones = request.form.get('observaciones', document.observaciones)
        
        DocumentModel.update(mysql, document)
        
        # Limpiar cache después de editar documento
        global search_cache
        search_cache = {}
        
        flash('Documento actualizado exitosamente!', 'success')
        return redirect(url_for('list_documents'))
    
    return render_template('edit_document.html', document=document)

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_document(id):
    document = DocumentModel.get_by_id(mysql, id)
    if document:
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.ruta_archivo)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            DocumentModel.delete(mysql, id)
            
            # Limpiar cache después de eliminar documento
            global search_cache
            search_cache = {}
            
            flash('Documento eliminado exitosamente!', 'success')
        except Exception as e:
            flash(f'Error al eliminar documento: {str(e)}', 'danger')
    
    return redirect(url_for('list_documents'))

@app.route('/generate-report', methods=['POST'])
@login_required
def generate_report():
    fecha_inicio = request.form.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin')
    
    if not fecha_inicio or not fecha_fin:
        flash('Por favor seleccione un rango de fechas válido', 'danger')
        return redirect(url_for('list_documents'))
    
    documents = DocumentModel.search_by_date(mysql, fecha_inicio, fecha_fin)
    
    # Asegurarse de que todos los documentos tengan usuario_nombre
    for doc in documents:
        if not hasattr(doc, 'usuario_nombre') or doc.usuario_nombre is None:
            doc.usuario_nombre = "Usuario Desconocido"
    
    return render_template('report.html', 
                         documents=documents, 
                         fecha_inicio=fecha_inicio, 
                         fecha_fin=fecha_fin)

def get_color_for_status(status):
    """Devuelve el color correspondiente al estado"""
    color_map = {
        'PAGADO': colors.HexColor('#28a745'),
        'SE ENVIÓ PRESUPUESTO': colors.HexColor('#17a2b8'),
        'TIENE ORDEN DE COMPRA': colors.HexColor('#007bff'),
        'SE ENVIÓ CONFORMIDAD': colors.HexColor('#6c757d'),
        'TIENE HES PARA FACTURAR': colors.HexColor('#ffc107'),
        'SE FACTURÓ': colors.HexColor('#6f42c1')
    }
    return color_map.get(status, colors.HexColor('#f8f9fa'))

def create_status_badge(status):
    """Crea un badge de estado para el PDF"""
    if status is None:
        status = "SIN ESTADO"
    
    color = get_color_for_status(status)
    style = ParagraphStyle(
        'StatusBadge',
        parent=getSampleStyleSheet()['Normal'],
        fontSize=7,
        textColor=colors.white,
        alignment=TA_CENTER,
        backColor=color,
        borderPadding=2,
        borderWidth=1,
        borderColor=color,
        borderRadius=3
    )
    return Paragraph(f' {status} ', style)

def safe_truncate(text, max_length):
    """Trunca texto de forma segura, manejando None"""
    if text is None:
        return "N/A"
    if len(text) > max_length:
        return text[:max_length] + '...'
    return text

@app.route('/download-pdf', methods=['POST'])
@login_required
def download_pdf():
    fecha_inicio = request.form.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin')
    
    if not fecha_inicio or not fecha_fin:
        flash('Por favor seleccione un rango de fechas válido', 'danger')
        return redirect(url_for('list_documents'))
    
    documents = DocumentModel.search_by_date(mysql, fecha_inicio, fecha_fin)
    
    # Asegurarse de que todos los documentos tengan usuario_nombre
    for doc in documents:
        if not hasattr(doc, 'usuario_nombre') or doc.usuario_nombre is None:
            doc.usuario_nombre = "Usuario Desconocido"
    
    # Crear PDF con márgenes optimizados
    buffer = io.BytesIO()
    pdf_doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm
    )
    
    # Estilos personalizados
    styles = getSampleStyleSheet()
    
    # Estilo para el título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        spaceAfter=6,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#2c3e50'),
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulos
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=11,
        spaceAfter=3,
        textColor=colors.HexColor('#495057'),
        fontName='Helvetica-Bold'
    )
    
    # Estilo normal
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#495057'),
        fontName='Helvetica'
    )
    
    # Estilo para información
    info_style = ParagraphStyle(
        'CustomInfo',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#6c757d'),
        fontName='Helvetica'
    )
    
    elements = []
    
    # Encabezado
    elements.append(Paragraph("SERVICIOS NAVALES BIMBO E.I.R.L.", title_style))
    elements.append(Paragraph("Reporte de Documentos", subtitle_style))
    elements.append(Spacer(1, 12))
    
    # Información del reporte
    elements.append(Paragraph(f"<b>Período:</b> {fecha_inicio} al {fecha_fin}", info_style))
    elements.append(Paragraph(f"<b>Fecha de generación:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}", info_style))
    elements.append(Paragraph(f"<b>Total de documentos:</b> {len(documents) if documents else 0}", info_style))
    elements.append(Spacer(1, 15))
    
    # Tabla de documentos
    if documents and len(documents) > 0:
        # Preparar datos de la tabla con textos truncados si es necesario
        table_data = [
            [
                Paragraph('<b>ID</b>', normal_style),
                Paragraph('<b>Embarcación</b>', normal_style),
                Paragraph('<b>Documento</b>', normal_style),
                Paragraph('<b>Estado</b>', normal_style),
                Paragraph('<b>Usuario</b>', normal_style),
                Paragraph('<b>Fecha</b>', normal_style)
            ]
        ]
        
        for doc in documents:
            # Manejar valores None de forma segura
            embarcacion = safe_truncate(doc.nombre, 20)
            documento = safe_truncate(doc.nombre_archivo, 25)
            usuario = safe_truncate(doc.usuario_nombre, 15)
            estado = doc.estado if doc.estado else "SIN ESTADO"
            fecha = doc.fecha_subida.strftime('%d/%m/%Y %H:%M') if doc.fecha_subida else "N/A"
            
            table_data.append([
                Paragraph(str(doc.id) if doc.id else "N/A", normal_style),
                Paragraph(embarcacion, normal_style),
                Paragraph(documento, normal_style),
                create_status_badge(estado),
                Paragraph(usuario, normal_style),
                Paragraph(fecha, normal_style)
            ])
        
        # Crear tabla con anchos de columna optimizados
        col_widths = [1.2*cm, 3.5*cm, 4.5*cm, 3.2*cm, 3.0*cm, 3.0*cm]
        
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Estilo de la tabla mejorado
        table.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            
            # Filas de datos
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # ID centrado
            ('ALIGN', (5, 1), (5, -1), 'CENTER'),  # Fecha centrada
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 1), (-1, -1), 3),
            ('RIGHTPADDING', (0, 1), (-1, -1), 3),
            ('TOPPADDING', (0, 1), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
            
            # Bordes y grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#adb5bd')),
            
            # Alternar colores de fila
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
        ]))
        
        # Añadir tabla al documento
        elements.append(KeepTogether(table))
        elements.append(Spacer(1, 15))
        
        # Resumen por estado
        estados_count = {}
        for doc in documents:
            estado = doc.estado if doc.estado else "SIN ESTADO"
            estados_count[estado] = estados_count.get(estado, 0) + 1
        
        if estados_count:
            elements.append(Paragraph("<b>Resumen por Estado</b>", subtitle_style))
            elements.append(Spacer(1, 8))
            
            summary_data = [
                [
                    Paragraph('<b>Estado</b>', normal_style),
                    Paragraph('<b>Cantidad</b>', normal_style),
                    Paragraph('<b>Porcentaje</b>', normal_style)
                ]
            ]
            
            total = len(documents)
            for estado, count in sorted(estados_count.items()):
                porcentaje = (count / total) * 100
                summary_data.append([
                    create_status_badge(estado),
                    Paragraph(str(count), normal_style),
                    Paragraph(f"{porcentaje:.1f}%", normal_style)
                ])
            
            summary_table = Table(summary_data, colWidths=[7*cm, 2.5*cm, 2.5*cm])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6c757d')),
                ('TEXTCOLor', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                ('ALIGN', (1, 1), (2, -1), 'CENTER'),
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            elements.append(summary_table)
    else:
        elements.append(Paragraph("No se encontraron documentos en el rango de fechas seleccionado.", normal_style))
    
    # Pie de página
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Reporte generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}", 
                            ParagraphStyle('Footer', parent=info_style, alignment=TA_CENTER)))
    elements.append(Paragraph("Servicios Navales Bimbo E.I.R.L. - RUC: 20541651889", 
                            ParagraphStyle('Footer', parent=info_style, alignment=TA_CENTER, fontSize=7)))
    
    # Generar PDF
    pdf_doc.build(elements)
    
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=reporte_documentos_{fecha_inicio}_a_{fecha_fin}.pdf'
    
    return response

if __name__ == '__main__':
    app.run(debug=True)