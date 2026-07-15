from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User, PasswordResetCode, UserLog


class LoginSerializer(serializers.Serializer):
    """支持用户名或邮箱登录"""
    username = serializers.CharField(label="用户名/邮箱")
    password = serializers.CharField(label="密码", write_only=True)

    def validate(self, data):
        username = data["username"]
        password = data["password"]

        # 判断是邮箱还是用户名
        if "@" in username:
            try:
                user_obj = User.objects.get(email=username)
                username = user_obj.username
            except User.DoesNotExist:
                raise serializers.ValidationError("该邮箱未注册")

        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("用户名/邮箱或密码错误")
        if not user.is_active:
            raise serializers.ValidationError("账号已被禁用")

        data["user"] = user
        return data


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label="确认密码")
    email = serializers.EmailField(required=True, label="邮箱")

    class Meta:
        model = User
        fields = ["username", "email", "password", "password2"]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("该邮箱已被注册")
        return value

    def validate(self, data):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError("两次密码不一致")
        return data

    def create(self, validated_data):
        validated_data.pop("password2")
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "phone", "company", "date_joined", "is_superuser", "is_active"]


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("该邮箱未注册")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(label="验证码")
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True, label="确认新密码")

    def validate(self, data):
        if data["new_password"] != data["new_password2"]:
            raise serializers.ValidationError("两次密码不一致")
        try:
            reset_code = PasswordResetCode.objects.get(code=data["code"])
        except PasswordResetCode.DoesNotExist:
            raise serializers.ValidationError("验证码无效")
        if not reset_code.is_valid():
            raise serializers.ValidationError("验证码已过期或已使用")
        data["reset_code"] = reset_code
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """登录状态下修改密码"""
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True, label="确认新密码")

    def validate(self, data):
        if data["new_password"] != data["new_password2"]:
            raise serializers.ValidationError("两次密码不一致")
        return data


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """管理员创建用户"""
    password = serializers.CharField(write_only=True, default="123456")
    password2 = serializers.CharField(write_only=True, label="确认密码", required=False)

    class Meta:
        model = User
        fields = ["username", "email", "password", "password2", "phone", "company"]

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("该用户名已被使用")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("该邮箱已被注册")
        return value

    def create(self, validated_data):
        validated_data.pop("password2", None)
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """管理员修改用户信息"""
    class Meta:
        model = User
        fields = ["username", "email", "phone", "company", "is_active"]


class AdminChangePasswordSerializer(serializers.Serializer):
    """管理员修改用户密码"""
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True, label="确认新密码")

    def validate(self, data):
        if data["new_password"] != data["new_password2"]:
            raise serializers.ValidationError("两次密码不一致")
        return data


class UserLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = UserLog
        fields = ["id", "username", "action", "action_display", "resource_type", "resource_id",
                  "detail", "ip_address", "created_at"]
