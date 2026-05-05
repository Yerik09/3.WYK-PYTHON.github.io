"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from usuarios import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Rutas raíz (Login y Logout se quedan aquí)
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # TODO lo que tenga que ver con la app usuarios va dentro de su propio include
    path('usuarios/', include('usuarios.urls')),

    # Rutas de la aplicación Inventario
    path('inventario/', include('inventario.urls')),

    path('compras/', include('compras.urls')),

    path('produccion/', include('produccion.urls')),

    path('ventas/', include('ventas.urls')),

    # Rutas de la aplicación Recetas
    path('recetas/', include('recetas.urls')),
]

# ESTA PARTE PERMITE QUE DJANGO SIRVA LAS IMÁGENES DE LA CARPETA MEDIA
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)