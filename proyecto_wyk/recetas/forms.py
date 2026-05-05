from django import forms
from django.forms import inlineformset_factory
from .models import Receta, DetalleReceta

# --------------------------------- FORMULARIO RECETA (MAESTRO) ---------------------------------
class RecetaForm(forms.ModelForm):
    class Meta:
        model = Receta
        fields = [
            'nombre_receta',
            'id_producto_fk_receta',
            'cantidad_base',
            'descripcion_receta',
            'estado_receta'
        ]
        widgets = {
            'nombre_receta': forms.TextInput(attrs={
                'placeholder': 'Ej: Receta Pan Blandito Tradicional',
                'class': 'input-wyk input-uppercase',
                'required': True
            }),
            'id_producto_fk_receta': forms.Select(attrs={
                'class': 'input-wyk select-item',
                'required': True
            }),
            'cantidad_base': forms.NumberInput(attrs={
                'placeholder': 'Cantidad que rinde esta receta',
                'class': 'input-wyk',
                'min': '1',
                'required': True
            }),
            'descripcion_receta': forms.Textarea(attrs={
                'class': 'input-wyk',
                'rows': 2,
                'placeholder': 'Pasos clave o descripción de la receta...'
            }),
            'estado_receta': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_nombre_receta(self):
        nombre = self.cleaned_data.get('nombre_receta').strip().upper()
        return nombre

# --------------------------------- FORMSET DE INSUMOS (DETALLE) ---------------------------------

# Este FormSet permite agregar múltiples materias primas a una sola receta
DetalleRecetaFormSet = inlineformset_factory(
    Receta,
    DetalleReceta,
    fields=[
        'id_materia_prima_fk_det_rec',
        'cantidad_insumo_base'
    ],
    widgets={
        'id_materia_prima_fk_det_rec': forms.Select(attrs={
            'class': 'input-wyk select-item',
            'required': True
        }),
        'cantidad_insumo_base': forms.NumberInput(attrs={
            'class': 'input-wyk cantidad-input',
            'step': '0.001',
            'min': '0.001',
            'placeholder': 'Cant. Base',
            'required': True
        }),
    },
    extra=0, # Igual que en producción, se maneja dinámicamente con JS
    can_delete=True,
    fk_name='id_receta_fk_det_rec'
)