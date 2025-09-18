document.addEventListener('DOMContentLoaded', function() {
    // Mostrar/ocultar campo para otra embarcación
    const embarcacionSelect = document.getElementById('nombre_embarcacion');
    if (embarcacionSelect) {
        const otraEmbarcacionContainer = document.getElementById('otra-embarcacion-container');
        
        embarcacionSelect.addEventListener('change', function() {
            if (this.value === 'otro') {
                otraEmbarcacionContainer.style.display = 'block';
                document.getElementById('otra_embarcacion').setAttribute('required', '');
            } else {
                otraEmbarcacionContainer.style.display = 'none';
                document.getElementById('otra_embarcacion').removeAttribute('required');
            }
        });
    }
    
    // Validación de formularios
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Búsqueda en tiempo real (para documents.html)
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        const tableBody = document.getElementById('documents-table-body');
        
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.trim().toLowerCase();
            
            if (searchTerm.length >= 1) {
                fetch(`/api/documents?q=${encodeURIComponent(searchTerm)}`)
                    .then(response => response.json())
                    .then(data => {
                        updateTable(data);
                    })
                    .catch(error => console.error('Error:', error));
            } else {
                fetch('/api/documents')
                    .then(response => response.json())
                    .then(data => {
                        updateTable(data);
                    })
                    .catch(error => console.error('Error:', error));
            }
        });
        
        function updateTable(documents) {
            if (documents.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center py-4">
                            <div class="alert alert-warning mb-0">
                                No se encontraron documentos que coincidan con la búsqueda.
                            </div>
                        </td>
                    </tr>
                `;
                return;
            }
            
            let html = '';
            documents.forEach(doc => {
                // Determinar clase del badge según el estado
                let badgeClass = 'bg-light text-dark';
                let badgeText = doc.estado;
                
                if (doc.estado === 'SE ENVIÓ PRESUPUESTO') {
                    badgeClass = 'badge-estado-presupuesto';
                } else if (doc.estado === 'TIENE ORDEN DE COMPRA') {
                    badgeClass = 'badge-estado-orden';
                } else if (doc.estado === 'SE ENVIÓ CONFORMIDAD') {
                    badgeClass = 'badge-estado-conformidad';
                } else if (doc.estado === 'TIENE HES PARA FACTURAR') {
                    badgeClass = 'badge-estado-hes';
                } else if (doc.estado === 'SE FACTURÓ') {
                    badgeClass = 'badge-estado-facturado';
                } else if (doc.estado === 'PAGADO') {
                    badgeClass = 'badge-estado-pagado';
                }
                
                html += `
                    <tr>
                        <td>${doc.id}</td>
                        <td>${doc.nombre}</td>
                        <td>
                            <a href="/download/${doc.ruta_archivo}" class="text-decoration-none" target="_blank">
                                <i class="bi bi-file-earmark-arrow-down me-2"></i>${doc.nombre_archivo}
                            </a>
                        </td>
                        <td>
                            <span class="badge ${badgeClass}">${badgeText}</span>
                        </td>
                        <td>${new Date(doc.fecha_subida).toLocaleString('es-ES')}</td>
                        <td class="text-end">
                            <div class="btn-group" role="group">
                                <a href="/document/${doc.id}" class="btn btn-sm btn-outline-primary">
                                    <i class="bi bi-pencil-square"></i>
                                </a>
                                <form method="POST" action="/delete/${doc.id}" class="d-inline" 
                                      onsubmit="return confirm('¿Confirmas que deseas eliminar este documento?');">
                                    <button type="submit" class="btn btn-sm btn-outline-danger">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </form>
                            </div>
                        </td>
                    </tr>
                `;
            });
            
            tableBody.innerHTML = html;
        }
    }
});