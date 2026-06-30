from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse
import json

from .models import Venta, DetalleVenta
from inventario.models import Producto
from .forms import VentaForm, DetalleVentaFormSet


# ------------------------------ GESTIÓN DE VENTAS (CRUD) ------------------------------

@login_required
def lista_ventas(request):
    """ Lista las ventas. El ADMIN/CAJERO ve todas, otros roles ven las del día """
    rol_usuario = request.user.rol_fk_usuario.rol
    queryset = Venta.objects.all().order_by('-fecha_hora_venta')

    if rol_usuario in ['ADMIN', 'CAJERO']:
        ventas = queryset
    else:
        # Filtro de seguridad para que personal vea solo lo de hoy
        ventas = queryset.filter(fecha_hora_venta__date=timezone.now().date())

    return render(request, 'ventas/lista.html', {'ventas': ventas})


@login_required
def crear_venta(request):
    """
    Registra una nueva orden de venta.
    Si es Mesero: estado PENDIENTE.
    Si es Cajero/Admin: estado PAGADA/ENTREGADO y resta stock inmediatamente.
    """
    productos = Producto.objects.filter(estado_producto=True)
    rol_usuario = request.user.rol_fk_usuario.rol

    if request.method == 'POST':
        form = VentaForm(request.POST)
        formset = DetalleVentaFormSet(request.POST, prefix='detalles_set')

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # 1. Guardar Cabecera
                    nueva_venta = form.save(commit=False)
                    nueva_venta.id_usuario_fk_venta = request.user
                    nueva_venta.fecha_hora_venta = timezone.now()

                    # Lógica de estados según rol
                    if rol_usuario in ['ADMIN', 'CAJERO']:
                        nueva_venta.estado_pedido = 'ENTREGADO'
                        nueva_venta.estado_pago = 'PAGADA'
                    else:
                        # Meseros solo pueden crear ventas PENDIENTES
                        nueva_venta.estado_pedido = 'PENDIENTE'
                        nueva_venta.estado_pago = 'PENDIENTE'

                    nueva_venta.total_venta = 0
                    nueva_venta.save()

                    # 2. Guardar Detalles y manejar Stock
                    detalles = formset.save(commit=False)
                    total_calculado = 0

                    for detalle in detalles:
                        producto = detalle.id_producto_fk_det_venta

                        # Si es venta directa (Cajero/Admin), validamos y restamos stock de inmediato
                        if rol_usuario in ['ADMIN', 'CAJERO']:
                            if producto.cant_exist_producto < detalle.cantidad:
                                raise ValueError(f"Stock insuficiente para {producto.nombre_producto}")

                            producto.cant_exist_producto -= detalle.cantidad
                            producto.save()

                        detalle.id_venta_fk_det_venta = nueva_venta
                        detalle.sub_total = producto.valor_unitario_product * detalle.cantidad
                        total_calculado += detalle.sub_total
                        detalle.save()

                    # 3. Actualizar total final
                    nueva_venta.total_venta = total_calculado
                    nueva_venta.save()

                    messages.success(request, f"Venta #{nueva_venta.id_venta} registrada correctamente.")
                    return redirect('lista_ventas')
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Error en base de datos: {str(e)}")
        else:
            for error in form.non_field_errors(): messages.error(request, error)
            for field in form:
                for error in field.errors: messages.error(request, f"{field.label}: {error}")
    else:
        form = VentaForm()
        formset = DetalleVentaFormSet(prefix='detalles_set')

    return render(request, 'ventas/crear.html', {
        'form': form,
        'formset': formset,
        'productos': productos
    })


@login_required
def editar_venta(request, id_venta):
    """
    Permite modificar una orden de venta activa (PENDIENTE, PREPARANDO o ENTREGADA).
    Si está PAGADA o CANCELADA no se puede modificar.
    Si el pedido estaba ENTREGADO y se añaden nuevos productos o se aumenta la cantidad,
    el estado cambia automáticamente a PENDIENTE.
    """
    venta = get_object_or_404(Venta, id_venta=id_venta)
    rol_usuario = request.user.rol_fk_usuario.rol

    # Restricción absoluta: Ventas cerradas o anuladas no se editan
    if venta.estado_pago in ['PAGADA', 'CANCELADA']:
        messages.error(request,
                       f"La venta #{venta.id_venta} ya se encuentra {venta.estado_pago.lower()} y no puede ser modificada.")
        return redirect('lista_ventas')

    productos = Producto.objects.filter(estado_producto=True)

    if request.method == 'POST':
        form = VentaForm(request.POST, instance=venta)
        formset = DetalleVentaFormSet(request.POST, instance=venta, prefix='detalles_set')

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Guardado en memoria para evaluar cambios en los detalles antes de impactar
                    venta_editada = form.save(commit=False)

                    # Bandera para identificar si se requiere volver el pedido a PENDIENTE
                    requiere_reversion_estado = False

                    # Mapeamos cantidades previas de los detalles guardados para el control estricto de stock de ADMIN/CAJERO
                    cantidades_anteriores = {d.id_producto_fk_det_venta_id: d.cantidad for d in venta.detalles.all()}

                    # Procesamos las instancias del formset antes de impactar en la BD
                    detalles = formset.save(commit=False)

                    # Evaluar registros eliminados en el formulario
                    for objeto_eliminado in formset.deleted_objects:
                        if rol_usuario in ['ADMIN', 'CAJERO']:
                            # Si es Admin/Cajero devolvemos el stock al almacén de forma inmediata
                            prod = objeto_eliminado.id_producto_fk_det_venta
                            prod.cant_exist_producto += objeto_eliminado.cantidad
                            prod.save()
                        objeto_eliminado.delete()

                    # Evaluar inserciones y modificaciones de cantidades
                    for detalle in detalles:
                        producto = detalle.id_producto_fk_det_venta
                        cant_anterior = cantidades_anteriores.get(producto.id_producto, 0)

                        # Si la cantidad nueva supera la anterior, evaluamos el cambio de estado si estaba ENTREGADO
                        if detalle.cantidad > cant_anterior:
                            if venta.estado_pedido == 'ENTREGADO':
                                requiere_reversion_estado = True

                        # Sincronización del stock físico en tiempo real solo si el rol administrador o cajero opera la edición
                        if rol_usuario in ['ADMIN', 'CAJERO']:
                            diferencia = detalle.cantidad - cant_anterior
                            if diferencia > 0:  # Solicita más unidades de este producto
                                if producto.cant_exist_producto < diferencia:
                                    raise ValueError(
                                        f"Stock insuficiente para {producto.nombre_producto}. Disponible adicional: {producto.cant_exist_producto}")
                                producto.cant_exist_producto -= diferencia
                            elif diferencia < 0:  # Disminuyó la cantidad original
                                producto.cant_exist_producto += abs(diferencia)
                            producto.save()

                        # Recalcular subtotal de la línea de venta
                        detalle.sub_total = producto.valor_unitario_product * detalle.cantidad
                        detalle.save()

                    # Aplicar reversión de estado si se agregaron nuevos componentes a un pedido entregado
                    if requiere_reversion_estado:
                        venta_editada.estado_pedido = 'PENDIENTE'

                    # CORRECCIÓN DE LA SUMA GLOBAL: Recorremos los registros grabados reales asociados a la venta
                    total_calculado = 0
                    for d_actualizado in venta_editada.detalles.all():
                        total_calculado += d_actualizado.sub_total

                    # Actualizar total de la venta global
                    venta_editada.total_venta = total_calculado
                    venta_editada.save()

                    messages.success(request, f"Venta #{venta_editada.id_venta} modificada correctamente.")
                    return redirect('lista_ventas')

            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Error en base de datos al editar: {str(e)}")
        else:
            for error in form.non_field_errors(): messages.error(request, error)
            for field in form:
                for error in field.errors: messages.error(request, f"{field.label}: {error}")
    else:
        form = VentaForm(instance=venta)
        formset = DetalleVentaFormSet(instance=venta, prefix='detalles_set')

    return render(request, 'ventas/editar.html', {
        'form': form,
        'formset': formset,
        'productos': productos,
        'venta': venta
    })

@login_required
def detalle_venta(request, id_venta):
    """ Muestra la información completa de la venta y sus productos """
    venta = get_object_or_404(Venta, id_venta=id_venta)
    detalles = venta.detalles.all()
    return render(request, 'ventas/detalle.html', {
        'venta': venta,
        'detalles': detalles
    })


# ------------------------------ ACCIONES AJAX (FLUJO DE ESTADOS) ------------------------------

@login_required
def entregar_venta_ajax(request):
    """ Acción del Mesero/Admin: Cambia PENDIENTE -> ENTREGADO """
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            id_v = data.get('id_venta')
            venta = get_object_or_404(Venta, id_venta=id_v)

            # Verificación de permiso: El mesero no puede cobrar, solo entregar
            if venta.estado_pago != 'PENDIENTE':
                return JsonResponse({'success': False, 'message': 'Solo se pueden entregar pedidos pendientes de pago.'})

            venta.estado_pedido = 'ENTREGADO'
            venta.save()

            # Respondemos directamente para que JS maneje el SweetAlert sin persistir mensajes en sesión
            return JsonResponse({'success': True, 'message': 'Pedido marcado como ENTREGADO. Ya puede ser cobrado.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False}, status=400)


@login_required
def finalizar_venta_ajax(request):
    """ Acción del Cajero/Admin: Cambia ENTREGADO -> PAGADA y DESCUENTA stock """
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Seguridad de Rol: Solo CAJERO o ADMIN pueden realizar el cobro final
        if request.user.rol_fk_usuario.rol not in ['ADMIN', 'CAJERO']:
            return JsonResponse({'success': False, 'message': 'No tienes permisos para registrar pagos.'})

        try:
            data = json.loads(request.body)
            id_v = data.get('id_venta')

            with transaction.atomic():
                venta = get_object_or_404(Venta, id_venta=id_v)

                if venta.estado_pedido != 'ENTREGADO':
                    return JsonResponse(
                        {'success': False, 'message': 'El pedido debe marcarse como ENTREGADO antes de cobrar.'})

                if venta.estado_pago == 'PAGADA':
                    return JsonResponse({'success': False, 'message': 'Esta venta ya fue pagada.'})

                # 1. Validar y Restar stock en el momento del cobro
                detalles = venta.detalles.all()
                for item in detalles:
                    producto = item.id_producto_fk_det_venta
                    if producto.cant_exist_producto < item.cantidad:
                        return JsonResponse({
                            'success': False,
                            'message': f"Stock insuficiente para {producto.nombre_producto} (Disponible: {producto.cant_exist_producto})."
                        })

                    producto.cant_exist_producto -= item.cantidad
                    producto.save()

                # 2. Finalizar
                venta.estado_pago = 'PAGADA'
                venta.fecha_cambio_estado = timezone.now()
                venta.save()

            return JsonResponse({'success': True, 'message': 'Venta PAGADA e inventario actualizado correctamente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f"Error: {str(e)}"})
    return JsonResponse({'success': False}, status=400)


@login_required
def cancelar_venta_ajax(request):
    """ Cancela la venta. Requiere contraseña. Si ya estaba PAGADA, devuelve el stock """
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            # Solo el ADMIN o alguien con la clave puede anular ventas
            if not request.user.check_password(data.get('password')):
                return JsonResponse({'success': False, 'message': 'Contraseña incorrecta.'})

            venta = get_object_or_404(Venta, id_venta=data.get('id_venta'))

            if venta.estado_pago == 'CANCELADA':
                return JsonResponse({'success': False, 'message': 'Esta venta ya se encuentra cancelada.'})

            with transaction.atomic():
                # Si estaba PAGADA, revertimos el stock al almacén
                if venta.estado_pago == 'PAGADA':
                    for item in venta.detalles.all():
                        producto = item.id_producto_fk_det_venta
                        producto.cant_exist_producto += item.cantidad
                        producto.save()

                venta.estado_pago = 'CANCELADA'
                venta.estado_pedido = 'CANCELADO'
                venta.fecha_cambio_estado = timezone.now()
                venta.save()

            return JsonResponse({'success': True, 'message': 'Venta anulada correctamente. El stock ha sido devuelto.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False}, status=400)