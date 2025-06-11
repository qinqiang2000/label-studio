from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def prompts_list(request):
    """View for prompts page"""
    return render(request, 'base.html')
