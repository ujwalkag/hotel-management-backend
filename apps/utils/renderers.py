from rest_framework.renderers import JSONRenderer
import json


class PrettyJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        return json.dumps(data, indent=4, ensure_ascii=False).encode('utf-8')
