from .models import Producto, MateriaPrima

def alertas_stock_critico(request):
    # Definimos los umbrales críticos
    UMBRAL_PRODUCTO_MIN = 5   # Menos de 5 unidades es crítico
    UMBRAL_MATERIA_MIN = 2.0  # Menos de 2.0 kg/lt o unidades es crítico

    notificaciones = []

    # 1. Validar Productos Bajos
    # Corregido: se usa cant_exist_producto según tu models.py
    productos_bajos = Producto.objects.filter(
        cant_exist_producto__lte=UMBRAL_PRODUCTO_MIN,
        estado_producto=True
    )
    for prod in productos_bajos:
        notificaciones.append({
            'tipo': 'producto',
            'nombre': prod.nombre_producto,
            'mensaje': f"Stock crítico: Solo quedan {prod.cant_exist_producto} UN."
        })

    # 2. Validar Materias Primas Bajas
    # Coincide perfectamente con cantidad_exist_mat_prima según tu models.py
    materias_bajas = MateriaPrima.objects.filter(
        cantidad_exist_mat_prima__lte=UMBRAL_MATERIA_MIN,
        estado_materia_prima=True
    )
    for mat in materias_bajas:
        notificaciones.append({
            'tipo': 'materia',
            'nombre': mat.nombre_materia_prima,
            'mensaje': f"Insumo bajo: Quedan {mat.cantidad_exist_mat_prima:g} {mat.presentacion_mat_prima}."
        })

    # Retornamos las variables mapeadas
    return {
        'lista_notificaciones': notificaciones,
        'total_notificaciones': len(notificaciones)
    }