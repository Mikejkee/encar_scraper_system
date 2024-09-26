from drf_yasg import openapi

CAR_URL = openapi.Parameter('car_url', in_=openapi.IN_QUERY,
                            type=openapi.TYPE_STRING, required=True,
                            description='Ссылка на автомобиль')
CAR_VIN = openapi.Parameter('car_vin', in_=openapi.IN_QUERY,
                            type=openapi.TYPE_STRING, required=True,
                            description='VIN автомобиля')
TG_ID = openapi.Parameter('telegram_id', in_=openapi.IN_QUERY,
                          type=openapi.TYPE_STRING, required=True,
                          description='ID телеграм пользователя')
FILTER_ID = openapi.Parameter('filter_id', in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING, required=True,
                              description='ID фильтра поиска')
FILTER_TITLE = openapi.Parameter('filter_title', in_=openapi.IN_QUERY,
                                 type=openapi.TYPE_STRING, required=True,
                                 description='Название фильтра поиска')
FILTER_LINK = openapi.Parameter('filter_link', in_=openapi.IN_QUERY,
                                type=openapi.TYPE_STRING, required=True,
                                description='Ссылка фильтра поиска')
FILTER_BRAND = openapi.Parameter('filter_brand', in_=openapi.IN_QUERY,
                                 type=openapi.TYPE_STRING, required=True,
                                 description='Марка машины в фильтре поиска')
FILTER_MODEL = openapi.Parameter('filter_model', in_=openapi.IN_QUERY,
                                 type=openapi.TYPE_STRING, required=True,
                                 description='Модель машины в фильтре поиска')
FILTER_GENERATION = openapi.Parameter('filter_generation', in_=openapi.IN_QUERY,
                                      type=openapi.TYPE_STRING, required=True,
                                      description='Поколение машины в фильтре поиска')
