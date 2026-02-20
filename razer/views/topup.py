from rest_framework import status,serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from razer.playwright import  run_task
from drf_yasg.utils import swagger_auto_schema

class JawalkerTopupRequestSerializer(serializers.Serializer):
    value = serializers.CharField()
    player_id = serializers.CharField(required=False, allow_blank=True)
    product = serializers.ChoiceField(required=False, choices=[("jawaker", "Jawaker"), ("freefire", "Free Fire")])

class JawalkerTopupView(APIView):
    @swagger_auto_schema(request_body=JawalkerTopupRequestSerializer)
    def post(self, request):
        serializer = JawalkerTopupRequestSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            ok = run_task(
                value=data['value'],
                player_id=data.get('player_id'),
                product=data.get('product')
            )
            print(ok)
            return Response(ok, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
