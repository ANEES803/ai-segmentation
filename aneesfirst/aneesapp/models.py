from django.db import models

# Create your models here.
from django.db import models

class PaintTest(models.Model):
    original_image = models.ImageField(upload_to='original_images/')
    clicked_x = models.IntegerField(null=True, blank=True)
    clicked_y = models.IntegerField(null=True, blank=True)
    color = models.CharField(max_length=7, default='#ff0000') # Store hex color
    result_image = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PaintTest {self.pk} - {self.original_image.name}"
