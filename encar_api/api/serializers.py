import os
import requests
import base64

from rest_framework import serializers

from .utils.help_utils import extract_filename_from_photo_url, extract_car_id_from_photo_url


class PhotoListField(serializers.Field):
    def to_representation(self, photo_list):
        media_root = f'media'
        cars_photo = []
        host = os.environ.get("DJANGO_ALLOWED_HOSTS").split(" ")[0]
        port = os.environ.get("DJANGO_PORT")
        for car_photo in photo_list:

            car_id = extract_car_id_from_photo_url(car_photo['url'])
            file_name = extract_filename_from_photo_url(car_photo['url'])
            cars_photos_dir = os.path.join(media_root, 'cars_photos', str(car_id))

            file_dir_name = os.path.join(cars_photos_dir, file_name)
            if not os.path.exists(cars_photos_dir):
                os.makedirs(cars_photos_dir)

            response = requests.get(car_photo['url'])

            if response.status_code == 200:
                with open(file_dir_name, 'wb') as photo_file:
                    photo_file.write(response.content)

            if host != "localhost":
                cars_photo.append(f'{host}/{file_dir_name}')
            else:
                cars_photo.append(f'{host}:{port}/{file_dir_name}')

        return cars_photo


class CarSerializer(serializers.Serializer):
    car_id = serializers.IntegerField()
    car_id_from_photo = serializers.IntegerField()
    last_id = serializers.IntegerField()
    last_parsing_ts = serializers.DateTimeField()
    brand_id = serializers.IntegerField()
    model_id = serializers.IntegerField()
    fuel_id = serializers.IntegerField()
    transmission_id = serializers.IntegerField()
    price = serializers.IntegerField()
    mileage = serializers.CharField(max_length=32)
    manufacture_date = serializers.DateField()
    model_year = serializers.CharField(max_length=32)
    fuel = serializers.CharField(max_length=64)
    body_type = serializers.CharField(max_length=32)
    engine_capacity = serializers.CharField(max_length=32)
    transmission = serializers.CharField(max_length=128)
    color = serializers.CharField(max_length=64)
    registration_number = serializers.CharField(max_length=64)
    view_count = serializers.CharField(max_length=64)
    bookmarks = serializers.IntegerField()
    card_create_date = serializers.CharField(max_length=64)
    photo_list = PhotoListField()
    perfomance_check = serializers.CharField(max_length=2048)
    insurance_report = serializers.CharField(max_length=2048)
    option_list = serializers.JSONField()
    packet_list = serializers.JSONField()
    seller_name = serializers.CharField(max_length=64)
    seller_region = serializers.CharField(max_length=64)
    seller_comment = serializers.CharField()
    brand = serializers.CharField(max_length=128)
    model = serializers.CharField(max_length=128)
    mileage_km = serializers.IntegerField()
    engine_capacity_cc = serializers.IntegerField()


class InsuranceSerializer(serializers.Serializer):
    car_id = serializers.IntegerField()
    last_id = serializers.IntegerField()
    last_parsing_ts = serializers.DateTimeField()
    actual_date = serializers.DateField()
    car_specification = serializers.CharField(max_length=256)
    usage_history = serializers.CharField(max_length=256)
    owner_changes = serializers.CharField(max_length=256)
    total_loss = serializers.CharField(max_length=256)
    damage_my_car = serializers.CharField(max_length=256)
    damage_another_car = serializers.CharField(max_length=256)
    car_specification_table = serializers.JSONField()
    usage_history_table = serializers.JSONField()
    owner_changes_table = serializers.JSONField()
    total_loss_table = serializers.JSONField()
    damage_my_car_tables = serializers.JSONField()
    damage_another_car_tables = serializers.JSONField()
    damage_my_car_cnt = serializers.IntegerField()
    damage_my_car_cost = serializers.IntegerField()
    damage_another_car_cost = serializers.IntegerField()
    damage_another_car_cnt = serializers.IntegerField()
    total_loss_common = serializers.IntegerField()
    total_loss_threft = serializers.IntegerField()
    total_loss_flood = serializers.IntegerField()
    owner_changes_lp = serializers.IntegerField()
    owner_changes_o = serializers.IntegerField()


class InspectionSerializer(serializers.Serializer):
    car_id = serializers.IntegerField()
    car_specification = serializers.CharField(max_length=256)
    licence_plate = serializers.CharField(max_length=256)
    registration_date = serializers.DateField()
    fuel_id = serializers.IntegerField()
    warranty_type = serializers.CharField(max_length=64)
    model_year = serializers.IntegerField()
    warranty_period = serializers.CharField(max_length=128)
    transmission_id = serializers.IntegerField()
    vin = serializers.CharField(max_length=32)
    engine_type = serializers.CharField(max_length=32)
    mileage_gauge_status = serializers.JSONField()
    mileage = serializers.JSONField()
    vin_condition = serializers.JSONField()
    exhaust_gas = serializers.JSONField()
    tuning = serializers.JSONField()
    special_history = serializers.JSONField()
    change_of_use = serializers.JSONField()
    color = serializers.JSONField()
    main_options = serializers.JSONField()
    recall_target = serializers.JSONField()
    accident_history = serializers.CharField(max_length=256)
    simple_repair = serializers.CharField(max_length=256)
    special_notes = serializers.CharField(max_length=256)
    damages_table = serializers.JSONField()
    details_table = serializers.JSONField()
    photos = serializers.JSONField()
    inspector = serializers.CharField(max_length=256)
    informant = serializers.CharField(max_length=256)
    inspect_date = serializers.DateField()
    special_notes_inspector = serializers.CharField(max_length=256)
    inspection_photo_list = serializers.JSONField()
    fuel = serializers.CharField(max_length=64)
    transmission_type = serializers.CharField(max_length=64)
    last_id = serializers.IntegerField()
    last_parsing_ts = serializers.DateTimeField()
    warranty_period_from = serializers.DateField()
    warranty_period_to = serializers.DateField()


class FilterSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField(max_length=1024)
    link = serializers.CharField(max_length=2048)
    brand_code = serializers.CharField(max_length=64)
    model_code = serializers.CharField(max_length=64)
    generation_code = serializers.CharField(max_length=64)
    create_user = serializers.CharField(max_length=64)
