from django.conf import settings
from rest_framework import serializers

def validate_passport(image):
    
    if image.size > settings.PASSPORT_IMAGE_SIZE:
        raise serializers.ValidationError("Image exceeds 2MB")
    
    if image.content_type not in ["image/jpeg", "image/png"]:
        raise serializers.ValidationError("Only JPEG and PNG images are allowed.")
    
    return image
    