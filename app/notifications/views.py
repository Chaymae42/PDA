from django.shortcuts import render

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from .serializers import NotificationSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_notifications(request):
    """Notifications de l'utilisateur connecté"""
    notifications = Notification.objects.filter(user=request.user)
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_as_read(request, pk):
    """Marquer une notification comme lue"""
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marquée comme lue'})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification introuvable'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_as_read(request):
    """Marquer toutes les notifications comme lues"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({'message': 'Toutes les notifications marquées comme lues'})

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_notification(request, pk):
    """Supprimer une notification"""
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
        notification.delete()
        return Response({'message': 'Notification supprimée'})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification introuvable'}, status=404)
