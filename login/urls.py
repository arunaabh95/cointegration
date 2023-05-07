from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name= "home"),
    path('signup', views.signup, name="signup"),
    path('signin', views.signin, name="signin"),
    path('signout', views.signout, name="signout"),
    path('dashboard', views.dashboard, name="dashboard"),
    path('pairs', views.pairs, name="pairs"),
]
