from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('notifications', '0002_initial'),
    ]

    operations = [
        migrations.RenameField(model_name='notification', old_name='recipient', new_name='user'),
        migrations.RemoveField(model_name='notification', name='content_type'),
        migrations.RemoveField(model_name='notification', name='object_id'),
        migrations.RemoveField(model_name='notification', name='action_label'),
        migrations.RemoveField(model_name='notification', name='sent_email'),
        migrations.RemoveField(model_name='notification', name='sent_sms'),
        migrations.RemoveField(model_name='notification', name='sent_push'),
        migrations.RemoveField(model_name='notification', name='expires_at'),
        migrations.AddField(model_name='notification', name='channel', field=models.CharField(choices=[('IN_APP', 'In-App'), ('EMAIL', 'Email'), ('SYSTEM', 'System')], default='IN_APP', max_length=20)),
        migrations.AddField(model_name='notification', name='metadata', field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name='notification', name='related_id', field=models.PositiveBigIntegerField(blank=True, null=True)),
        migrations.AddField(model_name='notification', name='related_model', field=models.CharField(blank=True, default='', max_length=100), preserve_default=False),
        migrations.AlterField(model_name='notification', name='notification_type', field=models.CharField(choices=[('SESSION_SUBMITTED', 'Session Submitted'), ('SESSION_APPROVED', 'Session Approved'), ('SESSION_REJECTED', 'Session Rejected'), ('SESSION_DISTRIBUTED', 'Session Distributed'), ('SESSION_UNLOCKED', 'Session Unlocked'), ('ARREARS_PAYMENT_RECORDED', 'Arrears Payment Recorded'), ('FEE_WAIVER_APPROVED', 'Fee Waiver Approved')], db_index=True, max_length=64)),
        migrations.RemoveIndex(model_name='notification', name='notificatio_recipie_dde14f_idx'),
        migrations.RemoveIndex(model_name='notification', name='notificatio_notific_19df93_idx'),
        migrations.AddIndex(model_name='notification', index=models.Index(fields=['user', 'is_read', 'created_at'], name='notif_user_read_created_idx')),
        migrations.AddIndex(model_name='notification', index=models.Index(fields=['notification_type', 'created_at'], name='notif_type_created_idx')),
    ]
