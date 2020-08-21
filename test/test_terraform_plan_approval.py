import os
import unittest

import requests

api_base_url = os.environ['API_BASE_URL']


class TestTerraformPlanApproval(unittest.TestCase):

	def test_something(self):
		assert requests.get(f'{api_base_url}/').text == 'Hello, world!'
