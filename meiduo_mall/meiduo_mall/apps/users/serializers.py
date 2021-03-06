from rest_framework import serializers
from rest_framework_jwt.settings import api_settings
from .models import User
from django_redis import get_redis_connection
import re


class CreateUserSerializer(serializers.ModelSerializer):

    password2 = serializers.CharField(label='确认密码', write_only=True)
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    allow = serializers.CharField(label='同意协议', write_only=True)
    token = serializers.CharField(label='登录状态token', read_only=True)  # 增加token字段

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'password2', 'sms_code', 'mobile', 'allow','token')
        extra_kwargs = {
            'username': {
                'min_length': 5,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许5-20个字符的用户名',
                    'max_length': '仅允许5-20个字符的用户名',
                }
            },
            'password': {
                'write_only': True,
                'min_length': 8,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许8-20个字符的密码',
                    'max_length': '仅允许8-20个字符的密码',
                }
            }
        }

        def validate_mobile(self, value):
            if not re.match(r'^1[3-9]\d{9}$', value):
                raise serializers.ValidationError('手机号格式错误')
            return value

        def validate_allow(self, value):
            """检验用户是否同意协议"""
            if value != 'true':
                raise serializers.ValidationError('请同意用户协议')
            return value

            redis_conn = get_redis_connection('verify_codes')
            mobile = data['mobile']
            real_sms_code = redis_conn.get('sms_%s' % mobile)
            if real_sms_code is None:
                raise serializers.ValidationError('无效的短信验证码')
            if data['sms_code'] != real_sms_code.decode():
                raise serializers.ValidationError('短信验证码错误')

            return data

        def create(self, validated_data):

            del validated_data['password2']
            del validated_data['sms_code']
            del validated_data['allow']

            user = super().create(validated_data)

            user.set_password(validated_data['password'])
            user.save()

            jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
            jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
            payload = jwt_payload_handler(user)
            token = jwt_encode_handler(payload)
            user.token = token


            return user

