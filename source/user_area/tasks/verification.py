import os
import celery
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
import dns.resolver
from matrix_stats.celery import app
from user_area.models import BoundServer

VERIFICATION_EXPIRES_IN = timedelta(days=7)
VERIFICATION_REQUIRED_IN = timedelta(days=3)

def verify_txt_record(server):
    domain = server.server.hostname.split(":")[0]
    path = "_matrixstats.%s" % domain
    try:
        r = dns.resolver.query(path, "TXT")
    except (dns.resolver.NXDOMAIN, ):
        print("%s dns verification failed for %s" % (timezone.now(), domain))
        verification_expired = (
            server.last_verified_at is None or
            server.last_verified_at < timezone.now() - VERIFICATION_EXPIRES_IN
        )
        if server.is_verified and verification_expired:
            print("%s dns verification was EXPIRED for %s" % (timezone.now(), domain))
            server.is_verified = False
            server.save(update_fields=['is_verified'])
    else:
        print("%s dns verification SUCCESS for %s" % (timezone.now(),domain))
        code = r.response.answer[0][-1].strings[0]
        if code.decode() == str(server.verification_code):
            print("%s dns verification COMPLETE for %s" % (timezone.now(), domain))
            server.is_verified = True
            server.last_verified_at = timezone.now()
            server.save(update_fields=['is_verified', 'last_verified_at'])
        else:
            print("%s dns verification MISSMATCH for %s: %s vs %s" % (
                  timezone.now(), domain, code.decode(), str(server.verification_code)))


@app.task
def verify_bound_servers():
    # Exclude servers that was recently updated
    # or those who belows to deactivated users
    servers = BoundServer.objects.exclude(
        Q(is_verified=True) & Q(last_verified_at__gte=(timezone.now() - VERIFICATION_REQUIRED_IN)),
    ).exclude(user__is_active=False)
    for server in servers:
        verify_txt_record(server)

