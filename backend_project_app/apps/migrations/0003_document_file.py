# Generated migration for Document file field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apps', '0002_customuser_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='documents/', verbose_name='File tải lên'),
        ),
        migrations.AlterField(
            model_name='document',
            name='file_path',
            field=models.CharField(blank=True, max_length=1024, verbose_name='Đường dẫn file'),
        ),
    ]
