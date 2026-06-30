from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
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
    """
    productos = Producto.objects.filter(estado_producto=True)
    rol_usuario = request.user.rol_fk_usuario.rol

    # --- NUEVA LÓGICA: Calcular stock real para el modal ---
    for p in productos:
        apartado = DetalleVenta.objects.filter(
            id_producto_fk_det_venta=p,
            id_venta_fk_det_venta__estado_pago='PENDIENTE'
        ).aggregate(Sum('cantidad'))['cantidad__sum'] or 0

        # Este es el valor que el template ahora puede leer
        p.cant_real_disponible = max(0, p.cant_exist_producto - apartado)

    if request.method == 'POST':
        form = VentaForm(request.POST)
        formset = DetalleVentaFormSet(request.POST, prefix='detalles_set')

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    nueva_venta = form.save(commit=False)
                    nueva_venta.id_usuario_fk_venta = request.user
                    nueva_venta.fecha_hora_venta = timezone.now()

                    if rol_usuario in ['ADMIN', 'CAJERO']:
                        nueva_venta.estado_pedido = 'ENTREGADO'
                        nueva_venta.estado_pago = 'PAGADA'
                    else:
                        nueva_venta.estado_pedido = 'PENDIENTE'
                        nueva_venta.estado_pago = 'PENDIENTE'

                    nueva_venta.total_venta = 0
                    nueva_venta.save()

                    detalles = formset.save(commit=False)
                    total_calculado = 0

                    for detalle in detalles:
                        producto = detalle.id_producto_fk_det_venta

                        # Recalculamos dentro del atomic para máxima seguridad
                        apartado = DetalleVenta.objects.filter(
                            id_producto_fk_det_venta=producto,
                            id_venta_fk_det_venta__estado_pago='PENDIENTE'
                        ).aggregate(Sum('cantidad'))['cantidad__sum'] or 0

                        stock_real = producto.cant_exist_producto - apartado

                        if detalle.cantidad > stock_real:
                            raise ValueError(
                                f"No hay stock suficiente para {producto.nombre_producto}. (Disponible: {stock_real})")

                        if rol_usuario in ['ADMIN', 'CAJERO']:
                            producto.cant_exist_producto -= detalle.cantidad
                            producto.save()

                        detalle.id_venta_fk_det_venta = nueva_venta
                        detalle.sub_total = producto.valor_unitario_product * detalle.cantidad
                        total_calculado += detalle.sub_total
                        detalle.save()

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
    venta = get_object_or_404(Venta, id_venta=id_venta)
    rol_usuario = request.user.rol_fk_usuario.rol

    if venta.estado_pago in ['PAGADA', 'CANCELADA']:
        messages.error(request,
                       f"La venta #{venta.id_venta} ya se encuentra {venta.estado_pago.lower()} y no puede ser modificada.")
        return redirect('lista_ventas')

    productos = Producto.objects.filter(estado_producto=True)

    # --- AGREGA ESTA LÓGICA PARA EL STOCK REAL ---
    for p in productos:
        apartado = DetalleVenta.objects.filter(
            id_producto_fk_det_venta=p,
            id_venta_fk_det_venta__estado_pago='PENDIENTE'
        ).exclude(id_venta_fk_det_venta=venta).aggregate(Sum('cantidad'))['cantidad__sum'] or 0

        p.cant_real_disponible = max(0, p.cant_exist_producto - apartado)
    # ---------------------------------------------

    if request.method == 'POST':
        # ... (el resto de tu código POST permanece igual)
        form = VentaForm(request.POST, instance=venta)
        formset = DetalleVentaFormSet(request.POST, instance=venta, prefix='detalles_set')
        # ...
    else:
        form = VentaForm(instance=venta)
        formset = DetalleVentaFormSet(instance=venta, prefix='detalles_set')

    return render(request, 'ventas/editar.html',
                  {'form': form, 'formset': formset, 'productos': productos, 'venta': venta})

@login_required
def detalle_venta(request, id_venta):
    venta = get_object_or_404(Venta, id_venta=id_venta)
    return render(request, 'ventas/detalle.html', {'venta': venta, 'detalles': venta.detalles.all()})


# ------------------------------ ACCIONES AJAX ------------------------------

@login_required
def entregar_venta_ajax(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            venta = get_object_or_404(Venta, id_venta=data.get('id_venta'))
            if venta.estado_pago != 'PENDIENTE':
                return JsonResponse(
                    {'success': False, 'message': 'Solo se pueden entregar pedidos pendientes de pago.'})
            venta.estado_pedido = 'ENTREGADO'
            venta.save()
            return JsonResponse({'success': True, 'message': 'Pedido marcado como ENTREGADO.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False}, status=400)


@login_required
def finalizar_venta_ajax(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if request.user.rol_fk_usuario.rol not in ['ADMIN', 'CAJERO']:
            return JsonResponse({'success': False, 'message': 'No tienes permisos.'})

        try:
            data = json.loads(request.body)
            with transaction.atomic():
                venta = get_object_or_404(Venta, id_venta=data.get('id_venta'))
                if venta.estado_pedido != 'ENTREGADO':
                    return JsonResponse({'success': False, 'message': 'Debe estar ENTREGADO antes de cobrar.'})
                if venta.estado_pago == 'PAGADA':
                    return JsonResponse({'success': False, 'message': 'Ya fue pagada.'})

                for item in venta.detalles.all():
                    producto = item.id_producto_fk_det_venta
                    # Validar Stock Real (físico - otros pendientes)
                    apartado = DetalleVenta.objects.filter(
                        id_producto_fk_det_venta=producto,
                        id_venta_fk_det_venta__estado_pago='PENDIENTE'
                    ).exclude(id_venta_fk_det_venta=venta.id_venta).aggregate(Sum('cantidad'))['cantidad__sum'] or 0

                    if (producto.cant_exist_producto - apartado) < item.cantidad:
                        return JsonResponse(
                            {'success': False, 'message': f"Stock insuficiente para {producto.nombre_producto}."})

                    producto.cant_exist_producto -= item.cantidad
                    producto.save()

                venta.estado_pago = 'PAGADA'
                venta.fecha_cambio_estado = timezone.now()
                venta.save()
            return JsonResponse({'success': True, 'message': 'Venta PAGADA.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False}, status=400)


@login_required
def cancelar_venta_ajax(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            if not request.user.check_password(data.get('password')):
                return JsonResponse({'success': False, 'message': 'Contraseña incorrecta.'})
            venta = get_object_or_404(Venta, id_venta=data.get('id_venta'))
            with transaction.atomic():
                if venta.estado_pago == 'PAGADA':
                    for item in venta.detalles.all():
                        producto = item.id_producto_fk_det_venta
                        producto.cant_exist_producto += item.cantidad
                        producto.save()
                venta.estado_pago = 'CANCELADA'
                venta.estado_pedido = 'CANCELADO'
                venta.fecha_cambio_estado = timezone.now()
                venta.save()
            return JsonResponse({'success': True, 'message': 'Venta anulada.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False}, status=400)