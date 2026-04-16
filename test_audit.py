import os
import django
from dotenv import load_dotenv

# 1. Setup Django environment for a standalone script
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from contracts.models import Contract
from rest_framework.test import APIRequestFactory
from contracts.views import ContractViewSet

def run_test():
    load_dotenv()
    print("--- Starting AI Audit Test ---")
    
    # 2. Get the contract (Senior Tip: check if it exists first)
    contract = Contract.objects.first()
    if not contract:
        print("Error: No contract found in DB. Upload one via the browser first!")
        return

    print(f"Auditing Contract: {contract.title}")

    # 3. Simulate the API call
    factory = APIRequestFactory()
    view = ContractViewSet.as_view({'post': 'audit'})
    request = factory.post(f'/api/contracts/{contract.id}/audit/')
    
    # 4. Trigger logic and print results
    response = view(request, pk=contract.id)
    print(f"Status Code: {response.status_code}")
    print("Findings:", response.data)

if __name__ == "__main__":
    run_test()