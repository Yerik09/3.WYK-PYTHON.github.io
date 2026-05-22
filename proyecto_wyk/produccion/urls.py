from django.urls import path
from . import views

urlpatterns = [
    # --- RUTAS DE PRODUCCIÓN (GESTIÓN) ---
    # dominio.com/produccion/
    path('lista/', views.lista_produccion, name='lista_produccion'),

    # dominio.com/produccion/crear/
    path('crear/', views.crear_produccion, name='crear_produccion'),

    # dominio.com/produccion/detalle/1/
    path('detalle/<int:id_produccion>/', views.detalle_produccion, name='detalle_produccion'),

    # --- SEGURIDAD Y ACCIONES AJAX ---
    # Rutas para finalizar o cancelar órdenes de producción con validación
    path('finalizar-ajax/', views.finalizar_produccion_ajax, name='finalizar_produccion_ajax'),
    path('cancelar-ajax/', views.cancelar_produccion_ajax, name='cancelar_produccion_ajax'),

    # Ruta para obtener receta de producto
    path('obtener-receta-por-producto/', views.obtener_receta_por_producto, name='obtener_receta_por_producto'),
]