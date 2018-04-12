import json

def sync(self, filter_obj):
    r = self.api_call(
        "GET",
        "/sync?filter=%s" % json.dumps(filter_obj),
    )
    return r.json()
