from django.shortcuts import render
from django.http import HttpResponse
import requests
from IPython.display import HTML

subscription_key = "c19ebea57efd4bd082429665ab731840"
assert subscription_key
search_url = "https://api.cognitive.microsoft.com/bing/v7.0/search"

# Create your views here.

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

import boto3
import json
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.client('dynamodb')
dynamodbResource = boto3.resource('dynamodb')
try:
    table = dynamodb.create_table(
        TableName='dynamodb-search',
        KeySchema=[
            {
                'AttributeName': 'data',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'search_term',
                'KeyType': 'RANGE'
            }
        ],
         AttributeDefinitions=[
            {
                'AttributeName': 'data',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'search_term',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    )
    # Wait until the table exists.
    table.meta.client.get_waiter('table_exists').wait(TableName='dynamodb-search')

except dynamodb.exceptions.ResourceInUseException:
    # do something here as you require
    table = dynamodbResource.Table('dynamodb-search')
    pass


# Print out some data about the table.
print(table.item_count)


@api_view(['GET'])
def index(request):
    """
    List all code snippets, or create a new snippet.
    """
    if request.method == 'GET':
        if 'q' in request.GET:
            search_term = request.GET['q']
            print(search_term)
            response = table.scan(
                FilterExpression=Attr('search_term').eq(search_term)
            )
            items = response['Items']
            if len(items) > 0:
                print("not called")
                rowObjects = []
                for item in items:
                    rowObjects.append(json.loads(item['data']))
            else:
                print("called")
                headers = {"Ocp-Apim-Subscription-Key": subscription_key}
                params = {"q": search_term, "textDecorations": True, "textFormat": "HTML"}
                response = requests.get(search_url, headers=headers, params=params)
                response.raise_for_status()
                search_results = response.json()
                for v in search_results["webPages"]["value"]:
                    table.put_item(
                        Item={
                            'search_term': search_term,
                            'data': json.dumps(v),
                        }
                    )
                    print(table.item_count)
                rowObjects = search_results["webPages"]["value"]
            rows = "\n".join(["""<tr><td><a href=\"{0}\">{1}</a></td><td>{2}</td></tr>""".format(v["url"], v["name"], v["snippet"])
            for v in rowObjects])
            return HttpResponse("<table>{0}</table>".format(rows))
        else:
            message="You submitted nothing"
            return HttpResponse(message)

    '''elif request.method == 'POST':
        serializer = SnippetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST
    '''
    