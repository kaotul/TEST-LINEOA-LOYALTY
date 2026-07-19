from rest_framework import serializers

from points.models import PointBatch, PointTransaction


class PointTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointTransaction
        fields = ["id", "kind", "points", "purchase_amount", "note", "created_at"]


class ExpiringBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointBatch
        fields = ["remaining_points", "expires_at"]


class CustomerSummarySerializer(serializers.Serializer):
    """
    ใช้แสดงหน้า LIFF: คะแนนรวม, ประวัติการรับ-แลก, วันหมดอายุ (กติกาข้อ 3)
    """
    display_name = serializers.CharField()
    total_points = serializers.IntegerField()
    qr_token = serializers.UUIDField()
    nearest_expiry = serializers.DateTimeField(allow_null=True)
    expiring_soon_points = serializers.IntegerField()
    history = PointTransactionSerializer(many=True)
    expiring_batches = ExpiringBatchSerializer(many=True)
