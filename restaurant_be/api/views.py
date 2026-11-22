
from django.contrib.auth.models import User
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import viewsets, filters, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
    IsAdminUser,
)
from rest_framework.response import Response

from .permissions import IsOwnerOrReadOnly
from .models import Category, Restaurant, Review, SavedRestaurant
from .serializers import (
    CategorySerializer,
    RestaurantSerializer,
    ReviewSerializer,
    SavedRestaurantSerializer,
    RegisterSerializer,
)


# -----------------------------
# CATEGORY
# -----------------------------

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [AllowAny()]

        return [IsAdminUser()]


# -----------------------------
# RESTAURANTS
# -----------------------------

class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.select_related('category').all()
    serializer_class = RestaurantSerializer

    permission_classes = [
        IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    ]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
    ]

    filterset_fields = ['category']
    search_fields = ['name', 'city', 'state', 'description']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# -----------------------------
# REVIEWS
# -----------------------------

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related(
        'user',
        'restaurant',
    ).all()

    serializer_class = ReviewSerializer

    permission_classes = [
        IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    ]

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['restaurant']

    def perform_create(self, serializer):
        restaurant = serializer.validated_data['restaurant']

        if Review.objects.filter(
            user=self.request.user,
            restaurant=restaurant,
        ).exists():
            raise ValidationError({
                'restaurant': (
                    'You already reviewed this restaurant. '
                    'Please edit your existing review.'
                )
            })

        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        restaurant = serializer.validated_data.get(
            'restaurant',
            serializer.instance.restaurant,
        )

        duplicate = Review.objects.filter(
            user=serializer.instance.user,
            restaurant=restaurant,
        ).exclude(
            pk=serializer.instance.pk
        ).exists()

        if duplicate:
            raise ValidationError({
                'restaurant': 'You already reviewed this restaurant.'
            })

        serializer.save()

# SAVED RESTAURANTS (MY PLACES)

class SavedRestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = SavedRestaurantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return SavedRestaurant.objects.filter(
                user=self.request.user,
            ).select_related('restaurant')

        return SavedRestaurant.objects.none()

    def perform_create(self, serializer):
        restaurant = serializer.validated_data['restaurant']

        if SavedRestaurant.objects.filter(
            user=self.request.user,
            restaurant=restaurant,
        ).exists():
            raise ValidationError({
                'restaurant': (
                    'You already saved this restaurant. '
                    'Update its status in My Places.'
                )
            })

        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        restaurant = serializer.validated_data.get(
            'restaurant',
            serializer.instance.restaurant,
        )

        duplicate = SavedRestaurant.objects.filter(
            user=self.request.user,
            restaurant=restaurant,
        ).exclude(
            pk=serializer.instance.pk
        ).exists()

        if duplicate:
            raise ValidationError({
                'restaurant': 'You already saved this restaurant.'
            })

        serializer.save()


# CURRENT LOGGED-IN USER


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    profile = getattr(request.user, 'profile', None)

    return Response({
        'id': request.user.id,
        'username': request.user.username,
        'display_name': profile.display_name if profile else '',
        'is_superuser': request.user.is_superuser,
        'is_staff': request.user.is_staff,
    })


# USER REGISTRATION


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = RegisterSerializer

# ADMIN DASHBOARD


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard(request):

    if not request.user.is_staff:
        return Response(
            {'detail': 'Admin access required.'},
            status=403
        )

    return Response({
        'total_restaurants': Restaurant.objects.count(),
        'total_categories': Category.objects.count(),
        'total_reviews': Review.objects.count(),
        'total_users': User.objects.count(),
    })


# Admin Reviews Management

@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def admin_reviews(request):
    if not request.user.is_staff:
        return Response(
            {'detail': 'Admin access required.'},
            status=403
        )

    if request.method == 'GET':
        reviews = Review.objects.select_related(
            'user',
            'restaurant',
        ).order_by('-created_at')

        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    if request.method == 'DELETE':
        review_id = request.query_params.get('id')

        if not review_id:
            return Response(
                {'detail': 'Review ID is required.'},
                status=400
            )

        try:
            review = Review.objects.get(pk=review_id)
        except Review.DoesNotExist:
            return Response(
                {'detail': 'Review not found.'},
                status=404
            )

        review.delete()

        return Response(
            {'detail': 'Review deleted successfully.'},
            status=200
        )
