import json

def sync(self, filter_obj={}, since=None):
    qs = ""
    if filter_obj:
        qs += "filter=%s&" % json.dumps(filter_obj)
    if since:
        qs += "since=%s&" % since
    r = self.api_call(
        "GET",
        "/sync?%s" % qs,
    )
    return r.json()
