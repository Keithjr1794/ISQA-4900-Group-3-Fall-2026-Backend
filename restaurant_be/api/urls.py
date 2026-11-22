from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    RestaurantViewSet,
    ReviewViewSet,
    SavedRestaurantViewSet,
    RegisterView,
    current_user,
    admin_dashboard,
    admin_reviews,
    admin_users,
    admin_user_status,
)

router = DefaultRouter()

router.register(r'categories', CategoryViewSet)
router.register(r'restaurants', RestaurantViewSet)
router.register(r'reviews', ReviewViewSet)
router.register(
    r'saved-restaurants',
    SavedRestaurantViewSet,
    basename='saved-restaurant',
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', current_user, name='current-user'),
    path('admin/dashboard/', admin_dashboard, name='admin-dashboard'),
    path('admin/reviews/', admin_reviews, name='admin-reviews'),
    path('admin/users/', admin_users, name='admin-users'),
    path(
        'admin/users/<int:user_id>/status/',
        admin_user_status,
        name='admin-user-status',
    ),
    path('', include(router.urls)),
]