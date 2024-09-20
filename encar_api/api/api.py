import os
import requests

import pandas as pd
from django.core.files.base import ContentFile
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import *
from .utils.help_utils import (extract_car_id, cards_data_by_car_id, inspection_data_by_car_id,
                               insurance_data_by_car_id, inspection_data_by_car_vin)


config = {
    'psql_login': os.environ.get('SQL_USER'),
    'psql_password': os.environ.get('SQL_PASSWORD'),
    'psql_hostname': os.environ.get('SQL_HOST'),
    'psql_port': os.environ.get('SQL_PORT'),
    'psql_name_bd': os.environ.get('SQL_PARSER_DATABASE'),
    'psql_conn_type': 'postgres'
}

base_dir = os.path.dirname(os.path.abspath(__file__))


CAR_URL = openapi.Parameter('car_url', in_=openapi.IN_QUERY,
                            type=openapi.TYPE_STRING, required=True,
                            description='Ссылка на автомобиль')

CAR_VIN = openapi.Parameter('car_vin', in_=openapi.IN_QUERY,
                            type=openapi.TYPE_STRING, required=True,
                            description='VIN автомобиля')


class APICarInfoByUrl(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        tags=["cars"],
        operation_description='Получает информацию об автомобиле по его ссылке',
        manual_parameters=[CAR_URL],
    )
    def get(self, request):
        params = request.query_params
        car_url = params.get('car_url')

        if not car_url:
            return Response({'error': 'Car URL not found'}, status=400)

        car_id = extract_car_id(car_url)
        if not car_id:
            return Response({'error': "The link does not contain a car"}, status=400)

        card_info = cards_data_by_car_id(car_id, config, base_dir)
        if card_info.empty:
            return Response({'error': "The bad link (this car does not exist)"}, status=400)
        card_serializer_data = CarSerializer(card_info.iloc[0]).data

        inspection_info = inspection_data_by_car_id(car_id, config, base_dir)
        inspection_serializer_data = None
        if not inspection_info.empty:
            inspection_serializer_data = InspectionSerializer(inspection_info.iloc[0]).data

        insurance_info = insurance_data_by_car_id(car_id, config, base_dir)
        insurance_serializer_data = None
        if not insurance_info.empty:
            insurance_serializer_data = InsuranceSerializer(insurance_info.iloc[0]).data

        result_data = {
            'car_data': card_serializer_data,
            'inspection_data': inspection_serializer_data,
            'insurance_data': insurance_serializer_data
        }

        return Response(result_data, status=200)


class APICarInfoByVIN(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        tags=["cars"],
        operation_description='Получает информацию об автомобиле его VIN',
        manual_parameters=[CAR_VIN],
    )
    def get(self, request):
        params = request.query_params
        car_vin = params.get('car_vin')

        if not car_vin:
            return Response({'error': 'Car VIN not found'}, status=400)

        inspection_info = inspection_data_by_car_vin(car_vin, config, base_dir)

        if inspection_info.empty:
            return Response({'error': "Car with this VIN does not exist"}, status=400)

        inspection_info['last_parsing_ts'] = pd.to_datetime(inspection_info['last_parsing_ts'])
        newest_inspection_info = inspection_info[inspection_info[
                                                     'last_parsing_ts'] == inspection_info['last_parsing_ts'].max()]
        inspection_serializer_data = InspectionSerializer(newest_inspection_info.iloc[0]).data

        car_id = inspection_serializer_data['car_id']
        card_info = cards_data_by_car_id(car_id, config, base_dir)
        if card_info.empty:
            return Response({'error': "This car_id does not exist"}, status=400)
        card_serializer_data = CarSerializer(card_info.iloc[0]).data

        insurance_info = insurance_data_by_car_id(car_id, config, base_dir)
        insurance_serializer_data = None
        if not insurance_info.empty:
            insurance_serializer_data = InsuranceSerializer(insurance_info.iloc[0]).data

        result_data = {
            'car_data': card_serializer_data,
            'inspection_data': inspection_serializer_data,
            'insurance_data': insurance_serializer_data
        }

        return Response(result_data, status=400)
