from django.urls import path
from . import views

urlpatterns = [
    # --- RUTAS DE VENTAS (GESTIÓN POS) ---
    # dominio.com/ventas/lista/
    path('lista/', views.lista_ventas, name='lista_ventas'),

    # dominio.com/ventas/crear/
    path('crear/', views.crear_venta, name='crear_venta'),

    # dominio.com/ventas/editar/1/
    path('editar/<int:id_venta>/', views.editar_venta, name='editar_venta'),

    # dominio.com/ventas/detalle/1/
    path('detalle/<int:id_venta>/', views.detalle_venta, name='detalle_venta'),

    # --- SEGURIDAD Y ACCIONES AJAX ---
    # Rutas para procesar la entrega, el pago (descontar stock) o anular la venta
    path('entregar-ajax/', views.entregar_venta_ajax, name='entregar_venta_ajax'),
    path('finalizar-ajax/', views.finalizar_venta_ajax, name='finalizar_venta_ajax'),
    path('cancelar-ajax/', views.cancelar_venta_ajax, name='cancelar_venta_ajax'),
]