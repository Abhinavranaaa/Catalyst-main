from django.urls import path
from roadmap.views import generate_roadmap_view,getRoadmapJson

urlpatterns = [
    path("generate/", generate_roadmap_view, name="generate-roadmap"),
    path("get-roadmap", getRoadmapJson, name="fetch-roadmap"),
]