"""
URL configuration for GroqChat AI Assistant project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from chatbot import views as chatbot_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', chatbot_views.index_view, name='index'),
    path('api/', include('chatbot.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
