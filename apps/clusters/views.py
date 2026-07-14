"""集群 API 视图"""
from rest_framework import generics, permissions
from rest_framework.response import Response

from .models import Cluster
from .serializers import (
    ClusterCreateSerializer,
    ClusterDetailSerializer,
    ClusterListSerializer,
)
from apps.accounts.views import log_user_action


class ClusterListCreateView(generics.ListCreateAPIView):
    """GET: 获取所有集群 / POST: 创建集群"""
    permission_classes = [permissions.IsAuthenticated]
    queryset = Cluster.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ClusterCreateSerializer
        return ClusterListSerializer

    def perform_create(self, serializer):
        cluster = serializer.save()
        log_user_action(self.request.user, "create", "cluster", cluster.id,
                        f"创建集群: {cluster.name}", self.request)


class ClusterDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE: 集群详情"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ClusterDetailSerializer
    queryset = Cluster.objects.all()

    def perform_update(self, serializer):
        old = self.get_object()
        cluster = serializer.save()
        if old.name != cluster.name:
            log_user_action(self.request.user, "update", "cluster", cluster.id,
                            f"集群名: {old.name} → {cluster.name}", self.request)
        else:
            log_user_action(self.request.user, "update", "cluster", cluster.id,
                            f"更新集群: {cluster.name}", self.request)

    def perform_destroy(self, instance):
        log_user_action(self.request.user, "delete", "cluster", instance.id,
                        f"删除集群: {instance.name}", self.request)
        instance.delete()
