/* C:\xampp\htdocs\3.WYK-PYTHON.github.io\proyecto_wyk\compras\static\js\compras\proveedores.js */

/**
 * Consume la API de Colombia para llenar el select de 'Lugar de Expedición'.
 * Muestra "Seleccione Municipio..." inicialmente, pero mantiene la selección si hay una recarga.
 */

const API_COLOMBIA_CITIES = 'https://api-colombia.com/api/v1/City';

document.addEventListener("DOMContentLoaded", function () {
    const selectLugar = document.getElementById("id_lugar_expedicion");

    if (selectLugar) {
        // Capturamos el valor que el servidor devolvió después de la alerta (si existe)
        const valorPostAlerta = selectLugar.value;

        fetch(API_COLOMBIA_CITIES)
            .then(response => {
                if (!response.ok) throw new Error('Error al conectar con la API de ciudades');
                return response.json();
            })
            .then(data => {
                // 1. Limpieza e inserción de la opción por defecto
                selectLugar.innerHTML = '<option value="" disabled>Seleccione Municipio...</option>';

                // 2. Ordenar alfabéticamente
                data.sort((a, b) => a.name.localeCompare(b.name));

                // 3. Llenar el select
                data.forEach(ciudad => {
                    const option = document.createElement("option");
                    const nombreUpper = ciudad.name.toUpperCase().trim();

                    option.value = nombreUpper;
                    option.text = nombreUpper;

                    // 4. Si el valor coincide con lo que el usuario seleccionó antes de la alerta, lo marcamos
                    if (valorPostAlerta && nombreUpper === valorPostAlerta.toUpperCase().trim()) {
                        option.selected = true;
                    }

                    selectLugar.appendChild(option);
                });

                // 5. Si no había selección previa (formulario nuevo), dejar el placeholder visible
                if (!valorPostAlerta) {
                    selectLugar.value = "";
                }
            })
            .catch(error => {
                console.error("Error cargando lugares desde la API:", error);
                const errOption = document.createElement("option");
                errOption.text = "Error al cargar municipios";
                selectLugar.appendChild(errOption);
            });
    }
});