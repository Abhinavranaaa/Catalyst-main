from django.urls import path
from roadmap.views import generate_roadmap_view

urlpatterns = [
    path("generate/", generate_roadmap_view, name="generate-roadmap"),
]