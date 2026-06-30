/**
 * MOTOR DE REPORTES UNIVERSAL - WYK EXPRESS
 * @param {string} idTabla - ID HTML de la tabla (ej: 'tablaRoles')
 * @param {string} tituloReporte - Título que aparecerá en el PDF
 * @param {Array} columnasOmitir - Índices de columnas que no quieres exportar (ej: [4])
 */
function generarPDFGlobal(idTabla, tituloReporte, columnasOmitir = []) {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF('p', 'mm', 'a4');
    const anchoPagina = doc.internal.pageSize.width;
    const fecha = new Date().toLocaleDateString();

    const tablaElemento = document.getElementById(idTabla);
    if (!tablaElemento) {
        console.error("Error: No se encontró la tabla con ID: " + idTabla);
        return;
    }

    // 1. CAPTURA AUTOMÁTICA DE ENCABEZADOS
    const headerRow = [];
    const headerCells = tablaElemento.querySelectorAll('thead th');
    headerCells.forEach((cell, index) => {
        if (!columnasOmitir.includes(index)) {
            headerRow.push(cell.innerText.trim().toUpperCase());
        }
    });

    // 2. CAPTURA AUTOMÁTICA DE DATOS VISIBLES
    const bodyRows = [];
    const rows = tablaElemento.querySelectorAll('tbody tr');
    rows.forEach(row => {
        if (row.style.display !== 'none') {
            const rowData = [];
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, index) => {
                if (!columnasOmitir.includes(index)) {
                    rowData.push(cell.innerText.trim());
                }
            });
            bodyRows.push(rowData);
        }
    });

    // 3. DISEÑO CORPORATIVO WYK
    doc.setFont("helvetica", "bold");
    doc.setFontSize(18);
    doc.setTextColor(40, 40, 40);
    doc.text("PANADERIA WYK - " + tituloReporte.toUpperCase(), 15, 20);

    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(100);
    doc.text(`Reporte Administrativo | Generado el: ${fecha}`, 15, 27);

    doc.setDrawColor(61, 28, 2); // Café WYK
    doc.setLineWidth(0.8);
    doc.line(15, 30, anchoPagina - 15, 30);

    // 4. RENDERIZADO INTELIGENTE (Auto-ajuste de columnas)
    // Si hay más de 6 columnas (como en Usuarios), bajamos el tamaño de fuente
    const tamañoFuente = headerRow.length > 6 ? 7 : 8;

    doc.autoTable({
        head: [headerRow],
        body: bodyRows,
        startY: 35,
        theme: 'grid',
        margin: { left: 15, right: 15 },
        headStyles: {
            fillColor: [61, 28, 2],
            textColor: [255, 255, 255],
            halign: 'center',
            fontSize: tamañoFuente + 1
        },
        styles: {
            fontSize: tamañoFuente,
            font: "helvetica",
            cellPadding: 2,
            overflow: 'linebreak' // Permite que el texto largo salte de línea
        },
        // Colorear Estados automáticamente
        didParseCell: function(data) {
            const txt = data.cell.text[0] ? data.cell.text[0].toUpperCase() : "";
            if (txt === 'INACTIVO') data.cell.styles.textColor = [200, 0, 0];
            if (txt === 'ACTIVO') data.cell.styles.textColor = [0, 120, 0];
        }
    });

    // 5. DESCARGA
    doc.save(`WYK_Reporte_${tituloReporte.replace(/\s+/g, '_')}.pdf`);
}