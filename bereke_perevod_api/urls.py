from django.urls import path

from . import views

urlpatterns = [
    path('create/', views.CertCreateView.as_view(),name='file-create'),
    path('delete/<int:pk>', views.CertDeleteView.as_view(), name='file-delete'),

    path('listing/', views.CertListView.as_view(), name='files'),
    path('listing/<int:pk>/', views.CertDetailView.as_view(), name='file-detail'),
    path('download/<int:pk>/', views.FileDownloadView.as_view(), name='file-download'),
]