// C:\xampp\htdocs\3.WYK-PYTHON.github.io\proyecto_wyk\static\js\sidebar.js

function showModule(name) {
    // 1. Desactivar todos los módulos y botones
    document.querySelectorAll('.module').forEach(m => m.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    // 2. Activar el seleccionado
    const target = document.getElementById('mod-' + name);
    if (target) target.classList.add('active');

    // 3. Activar botón del menú
    const btn = document.querySelector(`.nav-item[onclick*="${name}"]`);
    if (btn) btn.classList.add('active');

    // 4. Cambiar título
    const titles = { dashboard: 'Dashboard', usuarios: 'Usuarios', productos: 'Productos' };
    const pageTitle = document.getElementById('pageTitle');
    if (pageTitle) pageTitle.textContent = titles[name] || name;
}

function toggleSidebar() {
    /**
     * Al alternar la clase 'active', el CSS configurado con 'width: max-content'
     * expandirá automáticamente el sidebar hasta cubrir el texto más largo.
     */
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.toggle('active');
    }
}

function updateDateTime() {
    const now = new Date();
    const options = {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    const el = document.getElementById('dateTime');
    if (el) el.textContent = now.toLocaleDateString('es-CO', options);
}

document.addEventListener('DOMContentLoaded', () => {
    updateDateTime();
    setInterval(updateDateTime, 60000);
});