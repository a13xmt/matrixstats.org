import json
import traceback

def prettify(data):
    return json.dumps(data, indent=4, sort_keys=True)

def serialize(ex):
    strace = traceback.format_exc()
    return json.dumps({
        'type': ex.__class__.__name__,
        'args': str(ex.args),
        'stacktrace': str(strace.split('\n'))
    })

def critical(msg):
    # FIXME send notification
    print(msg)
