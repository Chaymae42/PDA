
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from users.serializers import UserSerializer
from drf_spectacular.utils import extend_schema
from .serializers import LoginRequestSerializer

@extend_schema(
    request=LoginRequestSerializer,
    description="Connexion avec username et password - TEST DE MODIFICATION",
    responses={200: UserSerializer},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Connexion avec username et password"""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'error': 'Username et password requis'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(username=username, password=password)

    if not user:
        return Response(
            {'error': 'Identifiants invalides'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    if not user.is_active_account:
        return Response(
            {'error': 'Compte désactivé. Contactez l\'administrateur.'},
            status=status.HTTP_403_FORBIDDEN
        )
    # Générer tokens JWT
    refresh = RefreshToken.for_user(user)

    return Response({
        'message': 'Connexion réussie',
        'user': UserSerializer(user).data,
        'tokens': {
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Déconnexion"""
    return Response({'message': 'Déconnexion réussie'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Obtenir les infos de l'utilisateur connecté"""
    return Response(UserSerializer(request.user).data)
