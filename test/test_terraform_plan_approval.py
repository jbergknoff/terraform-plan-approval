import base64
import os
import unittest

import requests

api_base_url = os.environ['API_BASE_URL']


class TestTerraformPlanApproval(unittest.TestCase):

	def test_end_to_end(self):
		plan_contents = 'hello, world!'
		response = requests.post(f'{api_base_url}/plan', json={'plan_base64': base64.b64encode(plan_contents.encode('utf8')).decode('utf8')})
		self.assertEqual(response.status_code, 201)
		plan_id = response.json()['id']

		self.assertTrue(plan_contents in requests.get(f'{api_base_url}/plan/{plan_id}').text)
		self.assertEqual(requests.get(f'{api_base_url}/plan/{plan_id}/status').json()['status'], 'pending')
		response = requests.put(f'{api_base_url}/plan/{plan_id}/status', json={'status': 'approved'})
		self.assertEqual(response.status_code, 204)
		z = requests.get(f'{api_base_url}/plan/{plan_id}/status').json()['status']
		self.assertEqual(z, 'approved')

	def test_non_existent_plan(self):
		self.assertEqual(requests.get(f'{api_base_url}/plan/nonexistent-plan-id').status_code, 404)
