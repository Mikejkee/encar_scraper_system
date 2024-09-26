import os

import pandas as pd
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema

from .utils.API_parameters import (CAR_URL, CAR_VIN, TG_ID, FILTER_ID, FILTER_LINK, FILTER_MODEL, FILTER_TITLE,
                                   FILTER_BRAND, FILTER_GENERATION)
from .serializers import CarSerializer, InsuranceSerializer, InspectionSerializer, FilterSerializer
from .utils.help_utils import extract_car_id
from .utils.db_utils import load_data_from_bd, load_data_in_db


config = {
    'psql_login': os.environ.get('SQL_USER'),
    'psql_password': os.environ.get('SQL_PASSWORD'),
    'psql_hostname': os.environ.get('SQL_HOST'),
    'psql_port': os.environ.get('SQL_PORT'),
    'psql_name_bd': os.environ.get('SQL_PARSER_DATABASE'),
    'psql_conn_type': 'postgres'
}

base_dir = os.path.dirname(os.path.abspath(__file__))


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

        card_info = load_data_from_bd(config, 'select_cards_by_car_id.sql', base_dir,
                                      'encar', 'cards', params_values={'car_id': car_id},
                                      expanding=False)
        if card_info.empty:
            return Response({'error': "The bad link (this car does not exist)"}, status=400)
        card_serializer_data = CarSerializer(card_info.iloc[0]).data

        # inspection_info = load_data_from_bd(config, 'select_inspection_by_car_id.sql', base_dir,
        #                                     'encar', 'inspection_list',
        #                                     params_values={'car_id': car_id}, expanding=False)
        # inspection_serializer_data = None
        # if not inspection_info.empty:
        #     inspection_serializer_data = InspectionSerializer(inspection_info.iloc[0]).data
        #
        # insurance_info = load_data_from_bd(config, 'select_insurance_by_car_id.sql', base_dir,
        #                                    'encar', 'insurance_list',
        #                                    params_values={'car_id': car_id}, expanding=False)
        # insurance_serializer_data = None
        # if not insurance_info.empty:
        #     insurance_serializer_data = InsuranceSerializer(insurance_info.iloc[0]).data

        # result_data = {
        #     'car_data': card_serializer_data,
        #     'inspection_data': inspection_serializer_data,
        #     'insurance_data': insurance_serializer_data
        # }

        return Response(card_serializer_data, status=200)


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

        inspection_info = load_data_from_bd(config, 'select_inspection_by_car_vin.sql', base_dir,
                                            'encar', 'inspection_list',
                                            params_values={'vin': car_vin}, expanding=False)

        if inspection_info.empty:
            return Response({'error': "Car with this VIN does not exist"}, status=400)

        inspection_info['last_parsing_ts'] = pd.to_datetime(inspection_info['last_parsing_ts'])
        newest_inspection_info = inspection_info[inspection_info['last_parsing_ts'] ==
                                                 inspection_info['last_parsing_ts'].max()]
        inspection_serializer_data = InspectionSerializer(newest_inspection_info.iloc[0]).data

        car_id = inspection_serializer_data['car_id']
        card_info = load_data_from_bd(config, 'select_cards_by_car_id.sql', base_dir,
                                      'encar', 'cards', params_values={'car_id': car_id},
                                      expanding=False)
        if card_info.empty:
            return Response({'error': "This car_id does not exist"}, status=400)
        card_serializer_data = CarSerializer(card_info.iloc[0]).data

        # insurance_info = load_data_from_bd(config, 'select_insurance_by_car_id.sql', base_dir,
        #                                    'encar', 'insurance_list',
        #                                    params_values={'car_id': car_id}, expanding=False)
        # insurance_serializer_data = None
        # if not insurance_info.empty:
        #     insurance_serializer_data = InsuranceSerializer(insurance_info.iloc[0]).data
        #
        # result_data = {
        #     'car_data': card_serializer_data,
        #     'inspection_data': inspection_serializer_data,
        #     'insurance_data': insurance_serializer_data
        # }

        return Response(card_serializer_data, status=400)


class APIFilterInfoByTgId(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        tags=["filters"],
        operation_description='Получает информацию о фильтрах пользователя по tg id ',
        manual_parameters=[TG_ID],
    )
    def get(self, request):
        params = request.query_params
        telegram_id = params.get('telegram_id')

        if not telegram_id:
            return Response({'error': 'Telegram id not found'}, status=400)

        filters_info = load_data_from_bd(config, 'select_filters_by_telegram_id.sql', base_dir,
                                         'encar', 'searches', params_values={'create_user': telegram_id},
                                         expanding=False)
        if filters_info.empty:
            return Response({'error': "Filters created by this user does not exist)"}, status=400)
        filters_data = filters_info.to_dict(orient='records')
        filters_serializer_data = FilterSerializer(filters_data, many=True).data

        return Response(filters_serializer_data, status=200)


class APIFilterDeleteById(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        tags=["filters"],
        operation_description='Удаляет фильтр пользователя по его id ',
        manual_parameters=[TG_ID, FILTER_ID],
    )
    def get(self, request):
        params = request.query_params
        telegram_id = params.get('telegram_id')
        filter_id = params.get('filter_id')

        if not (telegram_id and filter_id):
            return Response({'error': 'All needed params(telegram_id, filter_id) not found'}, status=400)

        try:
            load_data_from_bd(config, 'delete_filter_by_id_tg-id.sql', base_dir, 'encar', 'searches',
                              params_values={'filter_id': filter_id, 'create_user': telegram_id}, expanding=False)
        except Exception as e:
            return Response({'error': f"Delete filter failed, exception {e}"}, status=400)

        return Response('Delete success', status=200)


class APIFilterCreate(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        tags=["filters"],
        operation_description='Создает фильтр машин',
        manual_parameters=[TG_ID, FILTER_TITLE, FILTER_LINK, FILTER_BRAND, FILTER_MODEL, FILTER_GENERATION],
    )
    def get(self, request):
        params = request.query_params

        required_params = ['telegram_id', 'title', 'link', 'brand_code', 'model_code', 'generation_code']
        params_dict = {param: params.get(param) for param in required_params}

        new_filter_df = pd.DataFrame([params_dict])
        new_filter_df.rename(columns={'telegram_id': 'create_user'}, inplace=True)

        if any(value is None or value == '' for value in params_dict.values()):
            return Response({'error': 'All needed params(telegram_id, title, link, brand, model, generation) '
                                      'not found'}, status=400)

        try:
            load_data_in_db(new_filter_df, config, 'encar', 'searches')
        except Exception as e:
            return Response({'error': f"Create filter failed, exception {e}"}, status=400)

        return Response('Create success', status=200)
