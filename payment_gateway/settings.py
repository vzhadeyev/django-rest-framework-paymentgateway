from django.conf import settings
from django.core.signals import setting_changed


class APISettings:
    prefix = None

    def __init__(self, prefix: str = None):
        self.prefix = prefix
        self._cached_attrs = set()

    def prefixed_attr(self, attr):
        if attr.startswith(self.prefix.upper()):
            return attr
        return "%s_%s" % (self.prefix.upper(), attr.upper())

    def __getattr__(self, attr):

        val = getattr(settings, self.prefixed_attr(attr))

        # Cache the result
        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    def reload(self):
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()


api_settings = APISettings('PAYMENT_GATEWAY')


def reload_api_settings(*args, **kwargs):
    setting = kwargs['setting']
    if setting == 'PAYMENT_GATEWAY':
        api_settings.reload()


setting_changed.connect(reload_api_settings)
