from rest_framework.throttling import SimpleRateThrottle


class PhoneCheckThrottle(SimpleRateThrottle):
    scope = 'phone_check_request'

    def get_cache_key(self, request, view):
        phone_number = request.data.get('phone_number', '')
        ident = f"{self.get_ident(request)}_{phone_number}"
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }