from django.shortcuts import render

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, UserCreateSerializer
from .permissions import IsAdmin
from notifications.models import Notification

User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def list_users(request):
    """Liste des utilisateurs"""
    role = request.query_params.get('role')

    if role:
        users = User.objects.filter(role=role)
    else:
        users = User.objects.all()

    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def create_user(request):
    """Créer un nouvel utilisateur"""
    serializer = UserCreateSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        # Notification
        Notification.objects.create(
            user=user,
            notification_type='user_created',
            title='Compte créé',
            message=f'Votre compte a été créé par {request.user.username}'
        )

        return Response({
            'message': 'Utilisateur créé avec succès',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsAdmin])
def update_user(request, pk):
    """Modifier un utilisateur"""
    try:
        user = User.objects.get(pk=pk)

        user.first_name = request.data.get('first_name', user.first_name)
        user.last_name = request.data.get('last_name', user.last_name)
        user.email = request.data.get('email', user.email)
        user.phone = request.data.get('phone', user.phone)
        user.role = request.data.get('role', user.role)

        # Mise à jour localisation pour livreur
        if user.role == 'livreur':
            user.latitude = request.data.get('latitude', user.latitude)
            user.longitude = request.data.get('longitude', user.longitude)

        user.save()

        return Response({
            'message': 'Utilisateur modifié avec succès',
            'user': UserSerializer(user).data
        })
    except User.DoesNotExist:
        return Response(
            {'error': 'Utilisateur introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def toggle_user_status(request, pk):
    """Activer/Désactiver un compte utilisateur"""
    try:
        user = User.objects.get(pk=pk)
        user.is_active_account = not user.is_active_account
        user.save()

        status_text = 'activé' if user.is_active_account else 'désactivé'

        # Notification
        Notification.objects.create(
            user=user,
            notification_type='user_deactivated',
            title=f'Compte {status_text}',
            message=f'Votre compte a été {status_text} par {request.user.username}'
        )

        return Response({
            'message': f'Compte {status_text} avec succès',
            'user': UserSerializer(user).data
        })

    except User.DoesNotExist:
        return Response(
            {'error': 'Utilisateur introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )