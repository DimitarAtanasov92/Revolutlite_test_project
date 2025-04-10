# Generated by Django 5.2 on 2025-04-09 14:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='id_document',
        ),
        migrations.RemoveField(
            model_name='user',
            name='selfie',
        ),
        migrations.AddField(
            model_name='user',
            name='birth_date',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='document_number',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='full_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='id_back',
            field=models.ImageField(blank=True, null=True, upload_to='ids/back/'),
        ),
        migrations.AddField(
            model_name='user',
            name='id_front',
            field=models.ImageField(blank=True, null=True, upload_to='ids/front/'),
        ),
        migrations.AddField(
            model_name='user',
            name='issue_date',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='needs_manual_review',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='selfie_video',
            field=models.FileField(blank=True, null=True, upload_to='selfie_videos/'),
        ),
    ]
