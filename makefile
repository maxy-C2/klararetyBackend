# Makefile

.PHONY: test

test:
	python manage.py test users

test-coverage:
	coverage run --source=users manage.py test users
	coverage report
	coverage html

pytest:
	pytest users/tests/
