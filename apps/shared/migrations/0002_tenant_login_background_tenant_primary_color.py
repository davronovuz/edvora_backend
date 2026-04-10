from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shared', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='login_background',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='tenants/backgrounds/',
                verbose_name='Login fon rasmi',
            ),
        ),
        migrations.AddField(
            model_name='tenant',
            name='primary_color',
            field=models.CharField(
                default='#1e40af',
                max_length=7,
                verbose_name='Asosiy rang',
            ),
        ),
    ]
