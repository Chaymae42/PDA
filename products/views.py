from django.shortcuts import render

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from .models import Product
from .serializers import ProductSerializer, ProductCreateSerializer
from users.permissions import IsAdmin
import pandas as pd

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def add_product_name(request):
    """
    ÉTAPE 1: Admin ajoute le nom du produit (non validé)
    """
    name = request.data.get('name')

    if not name:
        return Response(
            {'error': 'Nom du produit requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
# Vérifier si existe déjà
    if Product.objects.filter(name=name).exists():
        return Response(
            {'error': 'Un produit avec ce nom existe déjà'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Créer produit non validé
    product = Product.objects.create(
        name=name,
        is_validated=False,
        created_by=request.user
    )
    return Response({
        'message': 'Nom du produit ajouté. Veuillez le valider.',
        'product': ProductSerializer(product).data
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def validate_product(request, pk):
    """
    ÉTAPE 2: Admin valide le produit et ajoute les détails
    """
    try:
        product = Product.objects.get(pk=pk)

        if product.is_validated:
            return Response(
                {'error': 'Produit déjà validé'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Ajouter les détails
        product.description = request.data.get('description', '')
        product.unit = request.data.get('unit', 'unité')
        product.price = request.data.get('price', 0)
        product.stock_quantity = request.data.get('stock_quantity', 0)
        product.is_validated = True
        product.validated_at = timezone.now()
        product.save()

        return Response({
            'message': 'Produit validé et ajouté à la liste',
            'product': ProductSerializer(product).data
        })

    except Product.DoesNotExist:
        return Response(
            {'error': 'Produit introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_products(request):
    """Liste des produits validés"""
    validated = request.query_params.get('validated', 'true')

    if validated == 'false':
        # Admin peut voir les non validés
        if request.user.role == 'admin':
            products = Product.objects.filter(is_validated=False)
        else:
            return Response(
                {'error': 'Non autorisé'},
                status=status.HTTP_403_FORBIDDEN
            )
    else:
        products = Product.objects.filter(is_validated=True, is_active=True)

    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_products(request):
    """Rechercher des produits par nom"""
    query = request.query_params.get('q', '')

    products = Product.objects.filter(
        name__icontains=query,
        is_validated=True,
        is_active=True
    )

    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsAdmin])
def update_product(request, pk):
    """Modifier un produit"""
    try:
        product = Product.objects.get(pk=pk)

        product.name = request.data.get('name', product.name)
        product.description = request.data.get('description', product.description)
        product.unit = request.data.get('unit', product.unit)
        product.price = request.data.get('price', product.price)
        product.stock_quantity = request.data.get('stock_quantity', product.stock_quantity)
        product.save()

        return Response({
            'message': 'Produit modifié avec succès',
            'product': ProductSerializer(product).data
        })

    except Product.DoesNotExist:
        return Response(
            {'error': 'Produit introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdmin])
def delete_product(request, pk):
    """Supprimer un produit (soft delete)"""
    try:
        product = Product.objects.get(pk=pk)
        product.is_active = False
        product.save()

        return Response({
            'message': 'Produit supprimé avec succès'
        })

    except Product.DoesNotExist:
        return Response(
            {'error': 'Produit introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
@parser_classes([MultiPartParser, FormParser])
def import_products_excel(request):
    """
    Importer des produits depuis Excel
    """
    if 'file' not in request.FILES:
        return Response(
            {'error': 'Fichier requis'},
            status=status.HTTP_400_BAD_REQUEST
        )

    file = request.FILES['file']

    try:
        df = pd.read_excel(file)

        required_cols = ['name', 'unit', 'price']
        if not all(col in df.columns for col in required_cols):
            return Response(
                {'error': f'Colonnes requises: {", ".join(required_cols)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        created = 0
        errors = []

        for idx, row in df.iterrows():
            try:
                Product.objects.create(
                    name=row['name'],
                    description=row.get('description', ''),
                    unit=row['unit'],
                    price=float(row['price']),
                    stock_quantity=float(row.get('stock_quantity', 0)),
                    is_validated=True,
                    validated_at=timezone.now(),
                    created_by=request.user
                )
                created += 1
            except Exception as e:
                errors.append(f"Ligne {idx + 2}: {str(e)}")

        return Response({
            'message': f'{created} produits importés avec succès',
            'created': created,
            'errors': errors
        })
    except Exception as e:
        return Response(
            {'error': f'Erreur: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
