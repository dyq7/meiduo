import random

from django.http import HttpResponse
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from meiduo_mall.meiduo_mall.libs.captcha.captcha import captcha
from django_redis import get_redis_connection
import logging
from rest_framework.response import Response
from rest_framework import status
from meiduo_mall.celery_tasks.sms.tasks import send_sms_code
from . import constants
from .serializers import ImageCodeCheckSerializer
from .utils.yuntongxun.sms import CCP
# Create your views here.

logger = logging.getLogger('django')


class ImageCodeView(APIView):
    """图片验证码"""
    def get(self,request,image_code_id):
        text, image = captcha.generate_captcha()
        redis_conn = get_redis_connection("verify_codes")
        redis_conn.setex('img_%s' % image_code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)
        return HttpResponse(image, content_type='images/jpg')

class SMSCodeView(GenericAPIView):

    serializer_class = ImageCodeCheckSerializer

    def get(self, request, mobile):

        serializer = self.get_serializer(data=request.query_params)

        serializer.is_valid(raise_exception=True)

        sms_code = '%06d' % random.randint(0, 999999)
        redis_conn = get_redis_connection('verify_codes')

        pl = redis_conn.pipeline()
        pl.setex("sms_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        pl.setex("send_flag_%s" % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)
        pl.execute()

        expires = constants.SMS_CODE_REDIS_EXPIRES // 60
        send_sms_code.delay(mobile, sms_code, expires, constants.SMS_CODE_TEMP_ID)

        return Response({'message': 'ok'})