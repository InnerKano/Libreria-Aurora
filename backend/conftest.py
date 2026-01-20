import os


# Allow running pytest without pytest.ini by setting the default Django settings module.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


# Ensure Django is initialized for tests that hit DRF views.
try:
	import django

	django.setup()
except Exception:
	# Some pure unit tests may not need Django; if settings/env isn't available
	# these tests will still be able to run.
	pass
