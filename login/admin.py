from django.contrib import admin
from .models import Pair, User, Transaction

# Register your models here.
admin.site.register(Pair)
admin.site.register(User)
admin.site.register(Transaction)