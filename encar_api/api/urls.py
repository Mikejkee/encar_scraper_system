from django.urls import path, re_path
from rest_framework import routers
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from .api import APICarInfoByUrl, APICarInfoByVIN, APIFilterInfoByTgId, APIFilterDeleteById, APIFilterCreate

schema_view = get_schema_view(
   openapi.Info(
      title="Encar API",
      default_version='v1',
      contact=openapi.Contact(email="contact@snippets.local"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

router = routers.DefaultRouter()

urlpatterns = router.urls
urlpatterns += [
    re_path(r'^swagger(?P<id>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # Cars
    path('car/info/by_url/', APICarInfoByUrl.as_view(), name='car_info_by_url'),
    path('car/info/by_vin/', APICarInfoByVIN.as_view(), name='car_info_by_vin'),

    # Filters
    path('filter/info/', APIFilterInfoByTgId.as_view(), name='filters_info_by_tg'),
    path('filter/create/', APIFilterCreate.as_view(), name='filter_create'),
    path('filter/delete/', APIFilterDeleteById.as_view(), name='filter_delete_by_id_tg'),

]
