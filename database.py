#!/usr/bin/env python
"""
=============================================================
SCRIPT AUTONOME D'INITIALISATION DE LA BASE DE DONNÉES
Pour PDA_NEW - Utilise SQLAlchemy (indépendant de Django)
=============================================================

USAGE: python database.py

Ce script va:
1. Créer la base de données PostgreSQL 'ltra' si elle n'existe pas
2. Créer toutes les tables de l'application si elles n'existent pas
3. Créer un utilisateur admin par défaut
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean,
    DateTime, Numeric, ForeignKey, UniqueConstraint,
    inspect
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy_utils import database_exists, create_database
from datetime import datetime
from werkzeug.security import generate_password_hash
import sys

# ============================================================
# CONFIGURATION - Modifier selon votre environnement
# ============================================================
DB_CONFIG = {
    'user': 'postgres',
    'password': 'pda',
    'host': 'localhost',
    'port': '5432',
    'database': 'ltra'
}

DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

# ============================================================
# INITIALISATION SQLALCHEMY
# ============================================================
Base = declarative_base()

# ============================================================
# DÉFINITION DES TABLES (miroir de vos modèles Django)
# ============================================================

class User(Base):
    """Table users - correspond à app.users.models.User"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    password = Column(String(128), nullable=False)
    last_login = Column(DateTime, nullable=True)
    is_superuser = Column(Boolean, default=False)
    username = Column(String(150), unique=True, nullable=False)
    first_name = Column(String(150), default='')
    last_name = Column(String(150), default='')
    email = Column(String(254), default='')
    is_staff = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    date_joined = Column(DateTime, default=datetime.utcnow)
    
    # Champs personnalisés PDA
    role = Column(String(20), nullable=False)  # admin, vendeur, magasinier, livreur
    is_active_account = Column(Boolean, default=True)
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relations
    created_users = relationship('User', backref='creator', remote_side=[id])
    products = relationship('Product', back_populates='creator')
    notifications = relationship('Notification', back_populates='user')


class Product(Base):
    """Table products - correspond à app.products.models.Product"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    unit = Column(String(50), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, nullable=False)
    is_validated = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    validated_at = Column(DateTime, nullable=True)
    
    # Relations
    creator = relationship('User', back_populates='products')


class Order(Base):
    """Table orders - correspond à app.orders.models.Order"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(100), unique=True, nullable=False)
    seller_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    seller_name = Column(String(255), nullable=False)
    customer_name = Column(String(255), nullable=False)
    status = Column(String(20), default='pending')  # pending, confirmed, preparing, ready, cancelled, in_delivery, delivered
    total_amount = Column(Numeric(10, 2), nullable=False)
    is_paid = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    prepared_at = Column(DateTime, nullable=True)
    ready_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Relations utilisateurs
    magasinier_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    deliverer_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    deliverer_name = Column(String(255), nullable=True)
    
    # Annulation
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relations
    items = relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')
    history = relationship('OrderHistory', back_populates='order', cascade='all, delete-orphan')
    notifications = relationship('Notification', back_populates='order')


class OrderItem(Base):
    """Table order_items - correspond à app.orders.models.OrderItem"""
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit = Column(String(50), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    
    # Relations
    order = relationship('Order', back_populates='items')


class OrderHistory(Base):
    """Table order_history - correspond à app.orders.models.OrderHistory"""
    __tablename__ = 'order_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    action = Column(String(50), nullable=False)  # created, modified, confirmed, cancelled, etc.
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    user_role = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    order = relationship('Order', back_populates='history')


class Notification(Base):
    """Table notifications - correspond à app.notifications.models.Notification"""
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    notification_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    user = relationship('User', back_populates='notifications')
    order = relationship('Order', back_populates='notifications')


# ============================================================
# TABLES DJANGO ESSENTIELLES (pour compatibilité)
# ============================================================

class DjangoMigrations(Base):
    """Table de suivi des migrations Django"""
    __tablename__ = 'django_migrations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    app = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    applied = Column(DateTime, default=datetime.utcnow)


class DjangoContentType(Base):
    """Content types Django"""
    __tablename__ = 'django_content_type'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    app_label = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('app_label', 'model', name='django_content_type_app_label_model_uniq'),
    )


class AuthPermission(Base):
    """Permissions Django"""
    __tablename__ = 'auth_permission'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    content_type_id = Column(Integer, ForeignKey('django_content_type.id'), nullable=False)
    codename = Column(String(100), nullable=False)


class AuthGroup(Base):
    """Groupes Django"""
    __tablename__ = 'auth_group'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), unique=True, nullable=False)


class DjangoSession(Base):
    """Sessions Django"""
    __tablename__ = 'django_session'
    
    session_key = Column(String(40), primary_key=True)
    session_data = Column(Text, nullable=False)
    expire_date = Column(DateTime, nullable=False)


class TokenBlacklistOutstandingToken(Base):
    """JWT tokens actifs"""
    __tablename__ = 'token_blacklist_outstandingtoken'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    jti = Column(String(255), unique=True, nullable=False)


class TokenBlacklistBlacklistedToken(Base):
    """JWT tokens blacklistés"""
    __tablename__ = 'token_blacklist_blacklistedtoken'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    blacklisted_at = Column(DateTime, default=datetime.utcnow)
    token_id = Column(Integer, ForeignKey('token_blacklist_outstandingtoken.id'), unique=True, nullable=False)


# ============================================================
# FONCTIONS D'INITIALISATION
# ============================================================

def create_database_if_not_exists():
    """Crée la base de données PostgreSQL si elle n'existe pas"""
    print(f"\n📦 Vérification de la base de données '{DB_CONFIG['database']}'...")
    
    if not database_exists(DATABASE_URL):
        print(f"   ➜ Base de données non trouvée, création en cours...")
        create_database(DATABASE_URL)
        print(f"   ✅ Base de données '{DB_CONFIG['database']}' créée!")
    else:
        print(f"   ✅ Base de données '{DB_CONFIG['database']}' existe déjà")


def create_tables_if_not_exist(engine):
    """Crée toutes les tables si elles n'existent pas"""
    print("\n🔧 Vérification et création des tables...")
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    # Liste des tables à créer
    tables_to_create = [
        'users', 'products', 'orders', 'order_items', 'order_history',
        'notifications', 'django_migrations', 'django_content_type',
        'auth_permission', 'auth_group', 'django_session',
        'token_blacklist_outstandingtoken', 'token_blacklist_blacklistedtoken'
    ]
    
    for table_name in tables_to_create:
        if table_name in existing_tables:
            print(f"   ✅ Table '{table_name}' existe déjà")
        else:
            print(f"   ➜ Table '{table_name}' sera créée")
    
    # Créer toutes les tables manquantes
    Base.metadata.create_all(engine)
    print("\n   ✅ Toutes les tables ont été vérifiées/créées!")


def create_admin_user(session):
    """Crée un utilisateur admin par défaut si aucun n'existe"""
    print("\n👤 Vérification de l'utilisateur admin...")
    
    existing_admin = session.query(User).filter_by(is_superuser=True).first()
    
    if existing_admin:
        print(f"   ✅ Admin existe déjà: {existing_admin.username}")
        return
    
    # Créer l'admin
    admin = User(
        username='admin',
        email='admin@pda.com',
        password=generate_password_hash('admin123', method='pbkdf2:sha256'),
        first_name='Admin',
        last_name='PDA',
        role='admin',
        is_superuser=True,
        is_staff=True,
        is_active=True,
        is_active_account=True
    )
    
    session.add(admin)
    session.commit()
    
    print("   ✅ Utilisateur admin créé:")
    print("      📧 Username: admin")
    print("      🔑 Password: admin123")
    print("      ⚠️  CHANGEZ CE MOT DE PASSE EN PRODUCTION!")


def main():
    """Fonction principale"""
    print("=" * 60)
    print("🚀 INITIALISATION AUTOMATIQUE - PDA_NEW DATABASE")
    print("=" * 60)
    print(f"\n📋 Configuration:")
    print(f"   Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"   Database: {DB_CONFIG['database']}")
    print(f"   User: {DB_CONFIG['user']}")
    
    try:
        # Étape 1: Créer la base de données
        create_database_if_not_exists()
        
        # Étape 2: Connexion et création des tables
        engine = create_engine(DATABASE_URL)
        create_tables_if_not_exist(engine)
        
        # Étape 3: Créer l'admin
        Session = sessionmaker(bind=engine)
        session = Session()
        create_admin_user(session)
        session.close()
        
        print("\n" + "=" * 60)
        print("✅ INITIALISATION TERMINÉE AVEC SUCCÈS!")
        print("=" * 60)
        print("\n📌 Prochaines étapes:")
        print("   1. python manage.py migrate --fake-initial")
        print("   2. python manage.py runserver")
        print("\n🌐 Votre application est prête!")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        print("\n💡 Vérifiez que:")
        print("   - PostgreSQL est démarré")
        print("   - Les identifiants sont corrects")
        print("   - Le port 5432 est accessible")
        sys.exit(1)


if __name__ == "__main__":
    main()

