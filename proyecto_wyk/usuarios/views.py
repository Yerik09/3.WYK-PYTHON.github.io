from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import ProtectedError, Sum, Count
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
import json
from .models import Rol, Usuario
from django.db import connection

# Importación de modelos externos para las estadísticas del dashboard
from inventario.models import Producto
from ventas.models import Venta, DetalleVenta

# IMPORTANTE: Ahora importamos los nuevos formularios
from .forms import LoginForm, RolForm, UsuarioForm


# ------------------------------ AUTENTICACIÓN ------------------------------
def login_view(request):
    if request.user.is_authenticated:
        return redirect('inicio')

    if request.method == 'POST':
        num_doc_post = request.POST.get('username')
        password_post = request.POST.get('password')

        if num_doc_post:
            usuario_db = Usuario.objects.filter(num_doc=num_doc_post).first()
            if usuario_db:
                if not usuario_db.is_active:
                    messages.error(request, "Acceso denegado. Tu cuenta está inactiva. Contacta al administrador.")
                    return render(request, 'registration/login.html', {'form': LoginForm(request.POST)})

                if usuario_db.rol_fk_usuario and not usuario_db.rol_fk_usuario.estado_rol:
                    messages.error(request,
                                   f"Acceso denegado. El rol '{usuario_db.rol_fk_usuario.rol}' está inactivo. Contacta al administrador.")
                    return render(request, 'registration/login.html', {'form': LoginForm(request.POST)})

        user = authenticate(request, num_doc=num_doc_post, password=password_post)

        if user is not None:
            auth_login(request, user)
            return redirect('inicio')
        else:
            messages.error(request, "Número de documento o contraseña incorrectos.")
            return render(request, 'registration/login.html', {'form': LoginForm(request.POST)})
    else:
        form = LoginForm()

    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
    auth_logout(request)
    return redirect('login')


# ------------------------------ SEGURIDAD AJAX ------------------------------

@login_required
def verificar_password_ajax(request):
    """ Verifica la contraseña mediante AJAX para preConfirm de SweetAlert2 """
    if request.method == 'POST':
        password = request.POST.get('password')
        is_valid = request.user.check_password(password)
        return JsonResponse({'valid': is_valid})

    return JsonResponse({'valid': False}, status=400)


# ------------------------------ INICIO ------------------------------
@login_required
def inicio(request):
    rol_usuario = request.user.rol_fk_usuario.rol if request.user.rol_fk_usuario else None
    contexto = {}
    hoy = timezone.now().date()

    # ==================== LÓGICA PARA EL ADMINISTRADOR ====================
    if rol_usuario == 'ADMIN':
        # --- 1. TOP 5 PRODUCTOS MÁS VENDIDOS ---
        top_productos = (
            DetalleVenta.objects.filter(id_venta_fk_det_venta__estado_pago='PAGADA')
            .values('id_producto_fk_det_venta__nombre_producto')
            .annotate(total_vendido=Sum('cantidad'))
            .order_by('-total_vendido')[:5]
        )

        productos_labels = [item['id_producto_fk_det_venta__nombre_producto'] for item in top_productos]
        productos_datos = [int(item['total_vendido']) for item in top_productos]

        # --- 2. TENDENCIA DE VENTAS (ÚLTIMOS 7 DÍAS) ---
        fechas_7_dias = [hoy - timedelta(days=i) for i in range(6, -1, -1)]

        ventas_labels = [fecha.strftime('%d/%m') for fecha in fechas_7_dias]
        ventas_datos = []

        for fecha in fechas_7_dias:
            total_dia = Venta.objects.filter(
                fecha_hora_venta__date=fecha,
                estado_pago='PAGADA'
            ).aggregate(total=Sum('total_venta'))['total'] or 0
            ventas_datos.append(int(total_dia))

        # --- 3. BALANCE DE ESTADOS DE PAGO ---
        estados_pago = Venta.objects.values('estado_pago').annotate(cantidad=Count('id_venta'))

        estados_dict = {item['estado_pago']: item['cantidad'] for item in estados_pago}
        estados_labels = ['Pagada', 'Pendiente', 'Cancelada']
        estados_datos = [
            estados_dict.get('PAGADA', 0),
            estados_dict.get('PENDIENTE', 0),
            estados_dict.get('CANCELADA', 0)
        ]

        # Serialización segura en formato JSON para que JavaScript pueda interpretarlos
        contexto.update({
            'admin_prod_labels': json.dumps(productos_labels),
            'admin_prod_datos': json.dumps(productos_datos),
            'admin_ventas_labels': json.dumps(ventas_labels),
            'admin_ventas_datos': json.dumps(ventas_datos),
            'admin_estados_labels': json.dumps(estados_labels),
            'admin_estados_datos': json.dumps(estados_datos),
        })

    # ==================== LÓGICA PARA PANADERO Y PASTELERO ====================
    elif rol_usuario in ['PANADERO', 'PASTELERIA', 'PASTELERO']:
        # 1. Alertas de Stock Crítico (Menos o igual a 10 unidades en vitrina)
        stock_critico = Producto.objects.filter(
            estado_producto=True,
            tipo_producto__in=['PANADERIA', 'PASTELERIA'],
            cant_exist_producto__lte=10
        ).order_by('cant_exist_producto')[:8]

        critico_labels = [p.nombre_producto for p in stock_critico]
        critico_datos = [int(p.cant_exist_producto) for p in stock_critico]

        # 2. Productos más demandados en los últimos 7 días (Planificación de horneo)
        hace_una_semana = hoy - timedelta(days=7)

        demanda_produccion = (
            DetalleVenta.objects.filter(
                id_venta_fk_det_venta__fecha_hora_venta__date__gte=hace_una_semana,
                id_venta_fk_det_venta__estado_pago='PAGADA',
                id_producto_fk_det_venta__tipo_producto__in=['PANADERIA', 'PASTELERIA']
            )
            .values('id_producto_fk_det_venta__nombre_producto')
            .annotate(total_pedido=Sum('cantidad'))
            .order_by('-total_pedido')[:5]
        )

        demanda_labels = [item['id_producto_fk_det_venta__nombre_producto'] for item in demanda_produccion]
        demanda_datos = [int(item['total_pedido']) for item in demanda_produccion]

        contexto.update({
            'prod_critico_labels': json.dumps(critico_labels),
            'prod_critico_datos': json.dumps(critico_datos),
            'prod_demanda_labels': json.dumps(demanda_labels),
            'prod_demanda_datos': json.dumps(demanda_datos),
        })

    # ==================== LÓGICA PARA EL MESERO ====================
    elif rol_usuario == 'MESERO':
        # 1. Monitor de Vitrina: Productos con disponibilidad para ofrecer activamente
        productos_disponibles = Producto.objects.filter(
            estado_producto=True,
            cant_exist_producto__gt=0
        ).order_by('-cant_exist_producto')[:6]

        vitrina_labels = [p.nombre_producto for p in productos_disponibles]
        vitrina_datos = [int(p.cant_exist_producto) for p in productos_disponibles]

        # 2. Rendimiento personal: Pedidos creados por este mesero en el día actual
        total_ordenes_hoy = Venta.objects.filter(
            id_usuario_fk_venta=request.user,
            fecha_hora_venta__date=hoy
        ).count()

        contexto.update({
            'vitrina_labels': json.dumps(vitrina_labels),
            'vitrina_datos': json.dumps(vitrina_datos),
            'total_ordenes_hoy': total_ordenes_hoy,
        })

    # ==================== LÓGICA PARA EL CAJERO ====================
    elif rol_usuario == 'CAJERO':
        # 1. Monitoreo del flujo de caja efectivo de su turno hoy
        ingresos_hoy = Venta.objects.filter(
            fecha_hora_venta__date=hoy,
            estado_pago='PAGADA'
        ).aggregate(total=Sum('total_venta'))['total'] or 0

        # 2. Estado de cuentas de los pedidos recibidos el día de hoy
        ventas_cajero_hoy = Venta.objects.filter(fecha_hora_venta__date=hoy).values('estado_pago').annotate(cantidad=Count('id_venta'))
        cajero_dict = {item['estado_pago']: item['cantidad'] for item in ventas_cajero_hoy}

        cajero_labels = ['Pagada', 'Pendiente', 'Cancelada']
        cajero_datos = [
            cajero_dict.get('PAGADA', 0),
            cajero_dict.get('PENDIENTE', 0),
            cajero_dict.get('CANCELADA', 0)
        ]

        contexto.update({
            'cajero_ingresos_hoy': int(ingresos_hoy),
            'cajero_labels': json.dumps(cajero_labels),
            'cajero_datos': json.dumps(cajero_datos),
        })

    return render(request, 'usuarios/inicio.html', contexto)


# ------------------------------ FUNCIONES DE ROLES (CRUD - SOLO ADMIN) ------------------------------

@login_required
def lista_roles(request):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. No tienes permisos para gestionar roles.")
        return redirect('inicio')

    roles = Rol.objects.all().order_by('id_rol')
    return render(request, 'usuarios/rol/lista.html', {'roles': roles})


@login_required
def crear_rol(request):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. No tienes permisos para crear roles.")
        return redirect('inicio')

    form = RolForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, f"Rol '{form.cleaned_data['rol']}' creado correctamente.")
            return redirect('lista_roles')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
            for field in form:
                for error in field.errors:
                    messages.error(request, error)

    return render(request, 'usuarios/rol/crear.html', {
        'clasificaciones': Rol.Clasificacion.choices,
        'form': form
    })


@login_required
def editar_rol(request, id_rol):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. No tienes permisos para editar roles.")
        return redirect('inicio')

    rol = get_object_or_404(Rol, id_rol=id_rol)
    form = RolForm(request.POST or None, instance=rol)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, f"Rol '{rol.rol}' actualizado correctamente.")
            return redirect('lista_roles')
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, error)

    return render(request, 'usuarios/rol/editar.html', {
        'rol': rol,
        'clasificaciones': Rol.Clasificacion.choices,
        'form': form
    })


@login_required
def eliminar_rol(request, id_rol):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. No tienes permisos para eliminar roles.")
        return redirect('inicio')

    rol = get_object_or_404(Rol, id_rol=id_rol)

    if request.method == 'POST':
        password_confirm = request.POST.get('password_confirm')
        if not request.user.check_password(password_confirm):
            messages.error(request, "Acceso denegado. Contraseña incorrecta. Acción cancelada.")
            return redirect('lista_roles')

        try:
            nombre_eliminado = rol.rol
            rol.delete()
            messages.success(request, f"Rol '{nombre_eliminado}' eliminado definitivamente.")
        except ProtectedError:
            messages.error(request,
                           f"Acceso denegado. No se puede eliminar '{rol.rol}' porque tiene usuarios vinculados.")

    return redirect('lista_roles')


@login_required
def cambiar_estado_rol_ajax(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if request.user.rol_fk_usuario.rol != 'ADMIN':
            return JsonResponse({'success': False, 'message': 'Acceso denegado.'})

        try:
            data = json.loads(request.body)
            id_rol = data.get('id_rol')
            nuevo_estado = data.get('nuevo_estado')
            password = data.get('password')

            if not request.user.check_password(password):
                return JsonResponse({'success': False, 'message': 'Contraseña incorrecta.'})

            rol = Rol.objects.get(id_rol=id_rol)
            if rol.rol == 'ADMIN' and not nuevo_estado:
                return JsonResponse({'success': False, 'message': 'El rol ADMIN debe permanecer activo siempre.'})

            rol.estado_rol = nuevo_estado
            rol.save()

            accion = "activado" if nuevo_estado else "inactivado"
            return JsonResponse({'success': True, 'message': f"Rol '{rol.rol}' {accion} correctamente."})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Acceso no autorizado.'}, status=400)


# ------------------------------ FUNCIONES DE USUARIOS (CRUD - SOLO ADMIN) ------------------------------

@login_required
def lista_usuarios(request):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. No tienes permisos para gestionar usuarios.")
        return redirect('inicio')

    usuarios = Usuario.objects.all().select_related('rol_fk_usuario').order_by('id_usuario')
    roles_lista = Rol.objects.all().order_by('rol')

    return render(request, 'usuarios/usuario/lista.html', {
        'usuarios': usuarios,
        'roles_lista': roles_lista
    })


@login_required
def crear_usuario(request):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. No tienes permisos para crear usuarios.")
        return redirect('inicio')

    roles = Rol.objects.filter(estado_rol=True)
    form = UsuarioForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            nuevo_usuario = form.save(commit=False)
            nuevo_usuario.set_password(request.POST.get('password'))
            nuevo_usuario.estado_usuario = True
            nuevo_usuario.save()
            messages.success(request, f"Usuario '{nuevo_usuario.nombre}' creado exitosamente.")
            return redirect('lista_usuarios')
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, error)

    return render(request, 'usuarios/usuario/crear.html', {'roles': roles, 'form': form})


@login_required
def editar_usuario(request, id_usuario):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. No tienes permisos para editar usuarios.")
        return redirect('inicio')

    usuario_edit = get_object_or_404(Usuario, id_usuario=id_usuario)
    roles = Rol.objects.filter(estado_rol=True)
    form = UsuarioForm(request.POST or None, instance=usuario_edit)

    if request.method == 'POST':
        if form.is_valid():
            usuario_actualizado = form.save(commit=False)
            nueva_pass = request.POST.get('password')
            if nueva_pass and nueva_pass.strip():
                usuario_actualizado.set_password(nueva_pass)
            usuario_actualizado.save()
            messages.success(request, f"Usuario '{usuario_actualizado.nombre}' actualizado.")
            return redirect('lista_usuarios')
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, error)

    return render(request, 'usuarios/usuario/editar.html', {
        'usuario': usuario_edit,
        'roles': roles,
        'form': form
    })


@login_required
def eliminar_usuario(request, id_usuario):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. No tienes permisos.")
        return redirect('inicio')

    usuario_del = get_object_or_404(Usuario, id_usuario=id_usuario)

    if request.method == 'POST':
        password_confirm = request.POST.get('password_confirm')
        if not request.user.check_password(password_confirm):
            messages.error(request, "Contraseña de administrador incorrecta.")
            return redirect('lista_usuarios')

        if usuario_del == request.user:
            messages.error(request, "No puedes eliminar tu propia cuenta.")
            return redirect('lista_usuarios')

        try:
            nombre_eliminado = usuario_del.nombre
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM usuario WHERE id_usuario = %s", [id_usuario])
            messages.success(request, f"Usuario '{nombre_eliminado}' eliminado correctamente.")
        except Exception:
            messages.error(request, f"No se puede eliminar a '{usuario_del.nombre}' porque tiene registros asociados.")

    return redirect('lista_usuarios')


@login_required
def cambiar_estado_usuario_ajax(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if request.user.rol_fk_usuario.rol != 'ADMIN':
            return JsonResponse({'success': False, 'message': 'Acceso denegado.'})

        try:
            data = json.loads(request.body)
            id_u = data.get('id_usuario')
            nuevo_estado = data.get('nuevo_estado')
            password = data.get('password')

            if not request.user.check_password(password):
                return JsonResponse({'success': False, 'message': 'Acceso denegado. Contraseña incorrecta.'})

            usuario = Usuario.objects.get(id_usuario=id_u)
            if usuario == request.user and not nuevo_estado:
                return JsonResponse({'success': False, 'message': 'No puedes desactivar tu propia cuenta.'})

            usuario.estado_usuario = nuevo_estado
            usuario.save()

            accion = "activado" if nuevo_estado else "inactivado"
            return JsonResponse({'success': True, 'message': f"Usuario '{usuario.nombre}' {accion} correctamente."})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Acceso no autorizado.'}, status=400)