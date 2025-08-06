import base64

from django.core.files.base import ContentFile
from rest_framework import serializers


class Base64ImageField(serializers.ImageField):
    """A custom serializer field for handling base64-encoded images. """
    def to_internal_value(self, data):
        if self._is_base64(data):
            data = self._decode_base64(data)
        return super().to_internal_value(data)

    def _is_base64(self, data):
        return isinstance(data, str) and data.startswith('data:image')

    def _decode_base64(self, data):
        header, imgstr = data.split(';base64,')
        ext = header.split('/')[-1]
        return ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
