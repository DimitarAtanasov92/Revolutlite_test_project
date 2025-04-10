from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    id_front = models.ImageField(upload_to='ids/front/', null=True, blank=True)
    id_back = models.ImageField(upload_to='ids/back/', null=True, blank=True)
    selfie_video = models.FileField(upload_to='selfie_videos/', null=True, blank=True)

    is_verified = models.BooleanField(default=False)
    confidence_score = models.FloatField(null=True, blank=True)

    full_name = models.CharField(max_length=100, null=True, blank=True)
    birth_date = models.CharField(max_length=50, null=True, blank=True)
    document_number = models.CharField(max_length=50, null=True, blank=True)
    issue_date = models.CharField(max_length=50, null=True, blank=True)

    needs_manual_review = models.BooleanField(default=False)

