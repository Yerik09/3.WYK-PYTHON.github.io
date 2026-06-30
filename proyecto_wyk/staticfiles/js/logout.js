document.addEventListener('DOMContentLoaded', () => {
    const logoutLink = document.getElementById('logout-link');
    if (logoutLink) {
        logoutLink.addEventListener('click', (e) => {
            e.preventDefault();
            Swal.fire({
                title: '¿Cerrar Sesión?',
                text: "¿Estás seguro de que quieres salir?",
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#933e0d',
                cancelButtonColor: '#64748b',
                confirmButtonText: 'Sí, Cerrar Sesión'
            }).then((result) => {
                if (result.isConfirmed) {
                    document.getElementById('logout-form').submit();
                }
            });
        });
    }
});