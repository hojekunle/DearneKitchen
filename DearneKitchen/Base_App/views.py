from django.shortcuts import render
from django.http import HttpResponse

from Base_App.models import Items, ItemList, Feedback, AboutUs, BookTable

# Create your views here.

def HomeView(request):
    return render(request, 'home.html')

def AboutView(request):
    return render(request, 'about.html')

def MenuView(request):
    items = Items.oject.all()
    list = ItemList.objects.all()
    return render(request, 'menu.html', {'items': items, 'list': list})

def BookTableView(request):
    return render(request, 'book_table.html')

def FeedbackView(request):
    return HttpResponse("Hi, this is my feedback")
