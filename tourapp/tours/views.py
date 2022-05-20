from django.shortcuts import render
from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, generics, permissions, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, TourComment, Tour, TourRating, News, NewsComment, NewsAction, BookingTour, TourPrice, Payment
from .serializers import (UserSerializer, CreateTourCommentSerializer, TourSerializer,
                          TourCommentSerializer, AuthTourDetailSerializer, NewsSerializer, NewsCommentSerializer,
                          CreateNewsCommentSerializer, AuthNewsDetailSerializer,
                          BookingTourSerializer, PaymentSerializer, TourDetailSerializer, NewsDetailSerializer
                          )
from .paginators import TourPaginator
from .perms import CommentOwnerPermisson, BookingOwnerPermisson
from django.conf import settings

class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    parser_classes = [MultiPartParser, ]
    def get_permissions(self):
        if self.action == 'current_user':
            return [permissions.IsAuthenticated()]

        return [permissions.AllowAny()]

    @action(methods=['get'], url_path="current-user", detail=False)
    def current_user(self, request):
        return Response(self.serializer_class(request.user, context={'request': request}).data,
                        status=status.HTTP_200_OK)

class AuthInfo(APIView):

    def get(self, request):
        return Response(settings.OAUTH2_INFO, status=status.HTTP_200_OK)


class TourViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Tour.objects.filter(active=True)
    serializer_class = TourSerializer
    def get_queryset(self):
        tour = self.queryset

        q = self.request.query_params.get('kw')
        if q:
            tour = tour.filter(name__icontains = q)

        endpos = self.request.query_params.get('endpos')
        if endpos:
            tour = tour.filter(endPOS__icontains = endpos)
        return tour
class TourDetailViewSet(viewsets.ViewSet, generics.RetrieveAPIView):
    queryset = Tour.objects.filter(active=True)
    serializer_class = TourDetailSerializer

    def get_serializer_class(self):
        if self.request.user.is_authenticated:
            return AuthTourDetailSerializer

        return TourDetailSerializer
    def get_permissions(self):
        if self.action in ['add_comment', 'rating', 'booking']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    @action(methods=['post'], url_path='booking', detail=True)
    def booking(self, request, pk):
        childticketnumber = request.data.get('childticketnumber')
        adultticketnumber = request.data.get('adultticketnumber')
        if adultticketnumber != 0:
            c = BookingTour.objects.create(childticketnumber=childticketnumber,
                                           adultticketnumber = adultticketnumber,
                                           tour=self.get_object(),
                                           user=request.user)
            return Response(BookingTourSerializer(c, context={"request": request}).data, status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], url_path='idbooking', detail=False)
    def idBooking(self, request):
        c = BookingTour.objects.all().last()
        return Response(BookingTourSerializer(c, context={"request": request}).data, status=status.HTTP_200_OK)


    @action(methods=['post'], url_path='add-comment', detail=True)
    def add_comment(self, request, pk):
        content = request.data.get('content')
        if content:
            c = TourComment.objects.create(content=content,
                                       tour=self.get_object(),
                                       user=request.user)
            return Response(TourCommentSerializer(c).data, status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], url_path='comments', detail=True)
    def get_comments(self, request, pk):
        tour = self.get_object()
        comments = tour.tourcomments.select_related('user').filter(active=True)
        return Response(TourCommentSerializer(comments , context={'request': request}, many=True).data,
                        status=status.HTTP_200_OK)

    @action(methods=['post'], url_path='rating', detail=True)
    def rating(self, request, pk):
        tour = self.get_object()
        user = request.user

        r, _ = TourRating.objects.get_or_create(tour=tour, user=user)
        r.rating = request.data.get('rating', 0)
        try:
            r.save()
        except:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(data=AuthTourDetailSerializer(tour, context={'request': request}).data,
                        status=status.HTTP_200_OK)



class BookingTourViewSet(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView, generics.UpdateAPIView, generics.DestroyAPIView):
    queryset = BookingTour.objects.filter(active=True)
    serializer_class = BookingTourSerializer
    ermission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['payment']:
            return [permissions.IsAuthenticated()]
        if self.action in ['update', 'destroy']:
            return [BookingOwnerPermisson()]
        return [permissions.AllowAny()]

    @action(methods=['post'], url_path='payment', detail=True)
    def payment(self, request, pk):
        tatalmoney = request.data.get('totalmoney')
        if tatalmoney:
            c = Payment.objects.create(totalmoney=tatalmoney,
                                        bookingtour=self.get_object())
            return Response(PaymentSerializer(c).data, status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_400_BAD_REQUEST)


class TourCommentViewSet(viewsets.ViewSet,generics.CreateAPIView, generics.UpdateAPIView, generics.DestroyAPIView):
    queryset = TourComment.objects.filter(active=True)
    serializer_class = CreateTourCommentSerializer
    ermission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['update', 'destroy']:
            return [CommentOwnerPermisson()]

        return [permissions.IsAuthenticated()]

class NewsViewSet(viewsets.ViewSet,generics.ListAPIView):
    queryset = News.objects.filter(active=True)
    serializer_class = NewsSerializer

    def get_queryset(self):
        news = News.objects.filter(active=True)

        new = self.request.query_params.get('new')
        if new is not None:
            news = News.objects.filter(subjects__icontains=new)
        return news
class NewsDetailViewSet(viewsets.ViewSet, generics.RetrieveAPIView):
    queryset = News.objects.filter(active = True)
    serializer_class = NewsDetailSerializer

    def get_serializer_class(self):
        if self.request.user.is_authenticated:
            return AuthNewsDetailSerializer

        return NewsDetailSerializer

    def get_permissions(self):
        if self.action in ['add_comment', 'like']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    @action(methods=['post'], url_path='add-comment', detail=True)
    def add_comment(self, request, pk):
        content = request.data.get('content')
        if content:
            c = NewsComment.objects.create(content=content,
                                           news=self.get_object(),
                                           user=request.user)
            return Response(NewsCommentSerializer(c).data, status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], url_path='comments', detail=True)
    def get_comments(self, request, pk):
        new = self.get_object()
        comments = new.newscomments.select_related('user').filter(active=True)
        return Response(NewsCommentSerializer(comments, context={'request': request}, many=True).data,
                        status=status.HTTP_200_OK)

    @action(methods=['post'], url_path='like', detail=True)
    def like(self, request, pk):
        news = self.get_object()
        user = request.user

        l, _ = NewsAction.objects.get_or_create(news=news, user=user)
        l.active = not l.active
        try:
            l.save()
        except:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(data=AuthNewsDetailSerializer(news, context={'request': request}).data,
                        status=status.HTTP_200_OK)


class NewsCommentViewSet(viewsets.ViewSet,generics.CreateAPIView, generics.UpdateAPIView, generics.DestroyAPIView):
    queryset = NewsComment.objects.filter(active=True)
    serializer_class = CreateNewsCommentSerializer
    ermission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['update', 'destroy']:
            return [CommentOwnerPermisson()]

        return [permissions.IsAuthenticated()]


