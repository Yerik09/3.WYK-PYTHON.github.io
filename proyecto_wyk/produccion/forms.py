from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from .models import Produccion, DetalleProduccion


# --------------------------------- FORMULARIO PRODUCCIÓN ---------------------------------
class ProduccionForm(forms.ModelForm):
    class Meta:
        model = Produccion
        fields = [
            'nombre_produccion',
            'id_producto_fk_produccion',
            'id_receta_fk_produccion',
            'categoria_produccion',
            'cant_produccion',
            'descripcion_produccion',
            'estado_produccion'
        ]
        widgets = {
            'nombre_produccion': forms.TextInput(attrs={
                'placeholder': 'Ej: Lote Pan Blandito - Mañana',
                'class': 'input-wyk input-uppercase',
                'required': True
            }),
            'id_producto_fk_produccion': forms.Select(attrs={
                'class': 'input-wyk select-item',
                'required': True
            }),
            'id_receta_fk_produccion': forms.HiddenInput(),
            'categoria_produccion': forms.TextInput(attrs={
                'placeholder': 'Ej: Panadería / Pastelería',
                'class': 'input-wyk',
                'required': True
            }),
            'cant_produccion': forms.NumberInput(attrs={
                'placeholder': 'Cantidad a producir',
                'class': 'input-wyk',
                'min': '1',
                'required': True
            }),
            'descripcion_produccion': forms.Textarea(attrs={
                'class': 'input-wyk',
                'rows': 2,
                'placeholder': 'Observaciones adicionales sobre el proceso...'
            }),
            'estado_produccion': forms.Select(attrs={
                'class': 'input-wyk',
                'id': 'id_estado_produccion'
            }),
        }

    def clean_nombre_produccion(self):
        nombre = self.cleaned_data.get('nombre_produccion').strip().upper()
        return nombre


# --------------------------------- CLASE DE VALIDACIÓN PARA FORMSET ---------------------------------

class BaseInsumosProduccionFormSet(forms.BaseInlineFormSet):
    def clean(self):
        """ Valida que no se repita una materia prima y que las cantidades sean mayores a cero """
        super().clean()

        if any(self.errors):
            return

        ingredientes = []
        for form in self.forms:
            # Ignoramos formularios que están vacíos o marcados para eliminación
            if self.can_delete and self._should_delete_form(form):
                continue
            if not form.cleaned_data:
                continue

            # --- Validación de cantidad positiva ---
            cantidad = form.cleaned_data.get('cantidad_requerida')
            if cantidad is not None and cantidad <= 0:
                raise ValidationError("La cantidad requerida debe ser mayor a cero.")

            # --- Validación de duplicados ---
            materia_prima = form.cleaned_data.get('id_materia_prima_fk_det_produc')
            if materia_prima:
                if materia_prima.id_materia_prima in ingredientes:
                    raise ValidationError(
                        f"El insumo '{materia_prima.nombre_materia_prima}' ya fue agregado. No puedes ponerlo más de una vez."
                    )
                ingredientes.append(materia_prima.id_materia_prima)


# --------------------------------- FORMSET DE INSUMOS ---------------------------------

# Este FormSet permite agregar múltiples materias primas (insumos) a una sola producción
InsumosProduccionFormSet = inlineformset_factory(
    Produccion,
    DetalleProduccion,
    formset=BaseInsumosProduccionFormSet,
    fields=[
        'id_materia_prima_fk_det_produc',
        'cantidad_requerida'
    ],
    widgets={
        'id_materia_prima_fk_det_produc': forms.Select(attrs={
            'class': 'input-wyk select-item',
            'required': True
        }),
        'cantidad_requerida': forms.NumberInput(attrs={
            'class': 'input-wyk cantidad-input',
            'step': '0.001',
            'min': '0.001',
            'placeholder': 'Cant. (Kg/Lts/Und)',
            'required': True
        }),
    },
    extra=0,  # Usamos 0 para manejar la adición de filas dinámicamente con JavaScript
    can_delete=True
)