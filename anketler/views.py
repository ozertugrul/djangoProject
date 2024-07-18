from django.shortcuts import render
from django.template import loader

# Create your views here.
from django.http import HttpResponse

def index(request):

    template = loader.get_template('index.html')
    return HttpResponse(template.render())

def abc(request):

    template = loader.get_template('a.html')
    return HttpResponse(template.render())
