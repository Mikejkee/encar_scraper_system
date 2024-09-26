from django.db import models
from authentication.models import Registrator


class DBLog(Registrator):
    time = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10)
    message = models.TextField()
    filename = models.CharField(max_length=255)
    func_name = models.CharField(max_length=255)
    lineno = models.CharField(max_length=255)

    objects = models.Manager()

    class Meta:
        ordering = ['-time']
        verbose_name = "Log"
        verbose_name_plural = "Logs"

        db_table = 'db_log'
        indexes = [
            models.Index(fields=['time'],
                         name='ind_db_log_time'),
            models.Index(fields=['level'],
                         name='ind_db_log_level')
        ]

    def __str__(self):
        return f'{self.message}'
