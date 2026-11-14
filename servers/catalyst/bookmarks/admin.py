from django.contrib import admin

from .models import Bookmark, FlagSubmission

admin.site.register(Bookmark)
admin.site.register(FlagSubmission)
