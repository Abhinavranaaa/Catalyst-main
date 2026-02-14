from django.urls import path
from roadmap.views import generate_roadmap_view,getRoadmapJson,getListRoadmap

urlpatterns = [
    path("generate/", generate_roadmap_view, name="generate-roadmap"),
    path("get-roadmap", getRoadmapJson, name="fetch-roadmap"),
    path("roadmap-list",getListRoadmap, name = "search-roadmap")
]