from django.shortcuts import render
from .models import Contract
from .serializers import ContractSerializer
from rest_framework import viewsets,status
from rest_framework.decorators import action
from .services import contract_agent
from rest_framework.response import Response


class ContractViewSet(viewsets.ModelViewSet):
    queryset=Contract.objects.all()
    serializer_class=ContractSerializer

    @action(detail=True, methods=['post'])
    def audit(self, request, pk=None):
        """Triggers the agentic audit workflow for a specific contract"""
        contract=self.get_object()

        # 1 Read the text from the uploaded file
        try:
            with contract.file.open('r') as f:
                content=f.read()
        except Exception:
            return Respose({"error":"Could not read file"},status=status.HTTP_400_BAD_REQUEST)
        
        # 2 invoke the LangGraph Agent
        # we pass the text and get back a validated dictionary

        result=contract_agent.invoke({
            "contract_text":content,
            "audit_data":{},
            "errors":{}
        })

        if result["errors"]:
            return Response({"status":"failed","errors":result['errors']},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 3 update the database state (Senior move : persistence)

        contract.status="Audited"
        contract.save()

        # return clean, pydantic-validated JSON to react

        return Response({
            "status":"success",
            "audit_results":result["audit_data"]
        })