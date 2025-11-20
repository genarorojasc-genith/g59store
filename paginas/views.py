from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages
from .models import PaginaInformativa
from django import forms


def ver_pagina(request, slug):
    pagina = get_object_or_404(PaginaInformativa, slug=slug, activo=True)
    return render(request, 'paginas/ver_pagina.html', {
        'pagina': pagina,
    })



class PaginaForm(forms.ModelForm):
    class Meta:
        model = PaginaInformativa
        fields = ['titulo', 'contenido', 'activo']
        widgets = {
            'contenido': forms.Textarea(attrs={'rows': 10}),
        }


@login_required
def panel_paginas(request):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    paginas = PaginaInformativa.objects.order_by('slug')
    return render(request, 'paginas/panel_lista.html', {
        'paginas': paginas,
    })


@login_required
def editar_pagina(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    pagina = get_object_or_404(PaginaInformativa, pk=pk)

    if request.method == 'POST':
        form = PaginaForm(request.POST, instance=pagina)
        if form.is_valid():
            form.save()
            messages.success(request, 'Página guardada correctamente.')
            return redirect('paginas:panel_paginas')
    else:
        form = PaginaForm(instance=pagina)

    return render(request, 'paginas/panel_form.html', {
        'form': form,
        'pagina': pagina,
    })
