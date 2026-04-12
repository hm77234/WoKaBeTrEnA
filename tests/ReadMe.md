# Testcommand
pytest -s --cov=tests --cov-report=term-missing -q
coverage html


# Limitations

tests are with motherlang "deutsch" only

Somtimes an error ocurred after a new build of the image:

 FAILED tests/test_admin_1_selenium_functional.py::test_app_functionality_restorbackup - selenium.common.exceptions.TimeoutException: Message: 
 FAILED tests/test_admin_2_functional.py::test_app_functionality_add_user - assert 'teststudent' in '<!DOCTYPE html>\n<html>\n<head>\n  

a second test runs perfect ... 