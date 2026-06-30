/**
 * toads-sweetalert2.js
 * Sistema de notificaciones inteligente para Panadería WYK
 */

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('login-form');

    // 1. VALIDACIÓN DEL LADO DEL CLIENTE (Toast naranja en la esquina)
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            const userInput = loginForm.querySelector('input[name="username"]');
            const passwordInput = loginForm.querySelector('input[name="password"]');

            let errorMsg = "";

            if (!userInput.value.trim() || !passwordInput.value.trim()) {
                errorMsg = "Por favor, completa todos los campos.";
            }
            else if (isNaN(userInput.value)) {
                errorMsg = "El número de documento debe contener solo números.";
            }

            if (errorMsg) {
                e.preventDefault();
                Swal.fire({
                    toast: true,
                    icon: "warning",
                    title: errorMsg,
                    position: "top-end",
                    showConfirmButton: false,
                    showCloseButton: true, // Permite cerrar manualmente
                    timer: 3000,
                    timerProgressBar: true,
                    pauseOnHover: true,    // Detiene el tiempo al pasar el mouse
                    background: '#f5a623',
                    color: '#fff',
                    iconColor: '#fff',
                    didOpen: (toast) => {
                        toast.addEventListener('mouseenter', Swal.stopTimer)
                        toast.addEventListener('mouseleave', Swal.resumeTimer)
                    }
                });
            }
        });
    }
});

// 2. MANEJO DE MENSAJES DESDE EL BACKEND (Inteligente)
if (typeof Swal !== 'undefined') {

    // --- MANEJO DE ÉXITO ---
    if (typeof successMessage !== 'undefined' && successMessage && successMessage.trim() !== "") {
        Swal.fire({
            toast: true,
            icon: "success",
            title: successMessage,
            position: "top-end",
            showConfirmButton: false,
            showCloseButton: true,
            timer: 3000,
            timerProgressBar: true,
            pauseOnHover: true,
            background: '#28a745',
            color: '#fff',
            iconColor: '#fff',
            didOpen: (toast) => {
                toast.addEventListener('mouseenter', Swal.stopTimer)
                toast.addEventListener('mouseleave', Swal.resumeTimer)
            }
        });
    }

    // --- MANEJO DE ERRORES (Diferenciado por gravedad) ---
    if (typeof errorMessage !== 'undefined' && errorMessage && errorMessage.trim() !== "") {

        const esAccesoDenegado = errorMessage.toLowerCase().includes("denegado") ||
                                 errorMessage.toLowerCase().includes("inactiva") ||
                                 errorMessage.toLowerCase().includes("administrador");

        if (esAccesoDenegado) {
            // ALERTA CENTRAL GRANDE (X Roja) - Para Usuario Inactivo
            Swal.fire({
                icon: 'error',
                title: 'Error de acceso',
                text: errorMessage,
                confirmButtonColor: '#f5a623',
                confirmButtonText: 'OK',
                background: '#fff',
                color: '#000',
                allowOutsideClick: false
            });
        } else {
            // TOAST EN LA ESQUINA (Naranja) - Para Credenciales Incorrectas
            Swal.fire({
                toast: true,
                icon: "warning",
                title: errorMessage,
                position: "top-end",
                showConfirmButton: false,
                showCloseButton: true,
                timer: 4000,
                timerProgressBar: true,
                pauseOnHover: true, // Detiene el tiempo al pasar el mouse
                background: '#f5a623',
                color: '#fff',
                iconColor: '#fff',
                didOpen: (toast) => {
                    toast.addEventListener('mouseenter', Swal.stopTimer)
                    toast.addEventListener('mouseleave', Swal.resumeTimer)
                }
            });
        }
    }
}