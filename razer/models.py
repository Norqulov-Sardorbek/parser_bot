from django.db import models




class TaskAccounts(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    auth_key = models.CharField(max_length=255)
    gold_balance = models.FloatField(default=0.0)
    silver_balance = models.FloatField(default=0.0)

    def __str__(self):
        return self.email