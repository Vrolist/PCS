from django.shortcuts import render


def index(request):
    """Vue SPA 入口页"""
    return render(request, 'vue_index.html')
