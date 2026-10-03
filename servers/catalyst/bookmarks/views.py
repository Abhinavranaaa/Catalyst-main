from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Bookmark, FlagSubmission
from .serializers import (
    BookmarkCreateSerializer,
    BookmarkReadSerializer,
    FlagSubmissionCreateSerializer,
    FlagSubmissionReadSerializer,
)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def bookmark_list_create(request):
    user_id = str(request.user.id)

    if request.method == "GET":
        bookmarks = Bookmark.objects.filter(user_id=user_id).order_by("-created_at")
        return Response(BookmarkReadSerializer(bookmarks, many=True).data)

    serializer = BookmarkCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    bookmark = Bookmark.objects.create(user_id=user_id, **serializer.validated_data)
    return Response(BookmarkReadSerializer(bookmark).data, status=status.HTTP_201_CREATED)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def bookmark_delete(request, bookmark_id):
    # 404 for both "doesn't exist" and "not yours" — don't let an
    # authenticated user distinguish the two for an ID they don't own.
    bookmark = Bookmark.objects.filter(id=bookmark_id, user_id=str(request.user.id)).first()
    if bookmark is None:
        return Response(status=status.HTTP_404_NOT_FOUND)

    bookmark.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def flag_create(request):
    serializer = FlagSubmissionCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    flag = FlagSubmission.objects.create(user_id=str(request.user.id), **serializer.validated_data)
    return Response(FlagSubmissionReadSerializer(flag).data, status=status.HTTP_201_CREATED)
