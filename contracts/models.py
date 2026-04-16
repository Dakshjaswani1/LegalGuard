from django.db import models
from pgvector.django import VectorField


class Contract(models.Model):
    title=models.CharField(max_length=25)
    file=models.FileField(upload_to='contracts/')
    status=models.CharField(max_length=50,default="pending")
    uploaded_at=models.DateTimeField(auto_now_add=True)

class ComplianceRules(models.Model):
    name=models.CharField(max_length=255)
    description=models.TextField()
    # optimized for BGE-based or QWEN embeddings
    embedding=VectorField(dimensions=768,null=True,blank=True)

    class Meta:
        indexes=[
            models.Index(fields=['name']),
        ]
