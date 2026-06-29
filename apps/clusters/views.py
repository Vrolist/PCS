"""集群 API 视图"""
from rest_framework import generics, permissions
from rest_framework.response import Response

from .models import Cluster
from .serializers import (
    ClusterCreateSerializer,
    ClusterDetailSerializer,
    ClusterListSerializer,
)


class ClusterListCreateView(generics.ListCreateAPIView):
    """GET: 获取用户的所有集群 / POST: 创建集群"""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cluster.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ClusterCreateSerializer
        return ClusterListSerializer


class ClusterDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE: 集群详情"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ClusterDetailSerializer

    def get_queryset(self):
        return Cluster.objects.filter(user=self.request.user)
