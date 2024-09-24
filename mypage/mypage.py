from flask import Flask, request, jsonify
import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)

# DynamoDB 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')
table = dynamodb.Table('Reservations')

@app.route('/mypage', methods=['GET'])
def mypage():
    # GET 요청에서 customer 파라미터를 받음
    customer = request.args.get('customer')
    
    if not customer:
        return jsonify({"error": "Missing required parameter: customer"}), 400
    
    try:
        # DynamoDB에서 Customer와 일치하는 항목들 검색
        response = table.scan(
            FilterExpression='Customer = :customer',
            ExpressionAttributeValues={':customer': customer}
        )
        items = response.get('Items', [])
        
        # 조회된 항목을 JSON 형식으로 변환
        reservations = []
        for item in items:
            reservations.append({
                'bookstore': item.get('BookstoreName'),
                'date': item.get('Date'),
                'time': item.get('Time')
            })
        
        # 결과 반환
        if not reservations:
            return jsonify({"message": "No reservations found for the customer"}), 404
        
        return jsonify(reservations), 200
    
    except ClientError as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "message": "The mypage application is running normally"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)