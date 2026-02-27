from django.urls import path
from roadmap.views import generate_roadmap_view,getRoadmapJson,getListRoadmap,process_roadmap_task,pollRoadmap

urlpatterns = [
    path("generate/", generate_roadmap_view, name="generate-roadmap"),
    path("get-roadmap", getRoadmapJson, name="fetch-roadmap"),
    path("roadmap-list",getListRoadmap, name = "search-roadmap"),
    path("task-be",process_roadmap_task,name="task-backend"),
    path("job",pollRoadmap,name="job")
]