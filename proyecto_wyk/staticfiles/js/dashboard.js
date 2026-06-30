// Gestión de tema
let currentTheme = 'light';

function toggleTheme() {
    try {
        currentTheme = currentTheme === 'light' ? 'dark' : 'light';
        document.body.setAttribute('data-theme', currentTheme);

        const themeIcon = document.querySelector('#themeToggle i');
        if (themeIcon) {
            themeIcon.className = currentTheme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
        }

        showNotification(`Tema cambiado a ${currentTheme === 'light' ? 'claro' : 'oscuro'}`, 'info');
    } catch (error) {
        console.error('Error al cambiar tema:', error);
    }
}

// Saludo dinámico (Corregido para respetar el nombre de Django)
function updateGreeting() {
    const greetingElement = document.querySelector('.greeting .s');
    if (!greetingElement) return;

    const nameSpan = greetingElement.querySelector('.n');
    const name = nameSpan ? nameSpan.textContent : 'Usuario';

    const hour = new Date().getHours();
    let greeting = '';

    if (hour < 12) greeting = 'Buen día';
    else if (hour < 18) greeting = 'Buenas tardes';
    else greeting = 'Buenas noches';

    greetingElement.innerHTML = `${greeting}, <span class="n">${name}</span>`;
}

// Notificaciones flotantes
function showNotification(message, type = 'info') {
    try {
        const notification = document.createElement('div');
        const colors = {
            'success': '#27ae60',
            'error': '#e74c3c',
            'info': '#3498db',
            'warning': '#f39c12'
        };

        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${colors[type] || colors.info};
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            z-index: 3000;
            font-weight: 500;
            transform: translateX(100%);
            opacity: 0;
            transition: all 0.3s ease;
        `;

        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
            notification.style.opacity = '1';
        }, 100);

        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            notification.style.opacity = '0';
            setTimeout(() => { notification.remove(); }, 300);
        }, 3000);
    } catch (error) {
        console.error('Error al mostrar notificación:', error);
    }
}

// Inicialización al cargar la página
document.addEventListener('DOMContentLoaded', () => {
    // 1. Configurar saludo inicial
    updateGreeting();
    setInterval(updateGreeting, 60000);

    // 2. Configurar botón de tema
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', (e) => {
            e.preventDefault();
            toggleTheme();
        });
    }

    // 3. Animación de entrada para la profile-card
    const profileCard = document.querySelector('.profile-card');
    if (profileCard) {
        profileCard.style.opacity = '0';
        profileCard.style.transform = 'translateY(20px)';
        setTimeout(() => {
            profileCard.style.transition = 'all 0.6s ease';
            profileCard.style.opacity = '1';
            profileCard.style.transform = 'translateY(0)';
        }, 300);
    }

    // 4. Bienvenida (Solo si no hay otros mensajes pendientes)
    if (!window.djangoMessages || window.djangoMessages.length === 0) {
        setTimeout(() => {
            showNotification('¡Bienvenido al Panel de Panadería WYK!', 'success');
        }, 1000);
    }

    // 5. Procesar mensajes de Django enviados desde el servidor
    if (window.djangoMessages && window.djangoMessages.length > 0) {
        window.djangoMessages.forEach(msg => {
            if (msg.text.includes("Acceso denegado")) {
                // Si es un error de seguridad, usamos SweetAlert para que sea impactante
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'error',
                        title: 'Seguridad',
                        text: msg.text,
                        confirmButtonColor: '#e74c3c'
                    });
                } else {
                    showNotification(msg.text, 'error');
                }
            } else {
                // Para el resto de mensajes (éxito, info), usamos tu notificación flotante
                showNotification(msg.text, msg.tag === 'error' ? 'error' : msg.tag);
            }
        });
    }
});