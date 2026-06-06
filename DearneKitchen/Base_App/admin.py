from django.contrib import admin
from Base_App.models import *
# Register your models here.

admin.site.register(ItemList) #must match classes in Models.py
admin.site.register(Items)
admin.site.register(AboutUs)
admin.site.register(Feedback)
admin.site.register(BookTable)