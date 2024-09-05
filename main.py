from flask import Flask, request, jsonify
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from boto3.dynamodb.conditions import Key

app = Flask(__name__)

# DynamoDB 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')
table = dynamodb.Table('Reservations')

# SNS 클라이언트 초기화
sns_client = boto3.client('sns', region_name='ap-northeast-2')  # region 설정 필요
sns_topic_arn = 'arn:aws:sns:ap-northeast-2:178020491921:success-reservation'  # 생성한 SNS 주제 ARN

def query_reservations(bookstore, date):
    try:
        # DynamoDB에서 KeyConditionExpression 수정
        response = table.query(
            KeyConditionExpression=Key('BookstoreName').eq(bookstore) & Key('Date').eq(date)
        )
        return response.get('Items', [])
    except (BotoCoreError, ClientError) as e:
        return str(e)
    
def create_reservation(bookstore, date, time, customer):
    try:
        response = table.put_item(
            Item={
                'BookstoreName': bookstore,
                'Date': date,
                'Time': time,
                'Customer': customer
            }
        )
        return response
    except (BotoCoreError, ClientError) as e:
        return str(e)

def send_sns_email(bookstore, date, time, customer):
    try:
        # SNS 메시지 생성
        message = f"New reservation created:\n\nBookstore: {bookstore}\nDate: {date}\nTime: {time}\nCustomer: {customer}"
        response = sns_client.publish(
            TopicArn=sns_topic_arn,
            Message=message,
            Subject="New Reservation Created"
        )
        return response
    except (BotoCoreError, ClientError) as e:
        return str(e)

@app.route('/reservations', methods=['GET', 'POST'])
def reservations():
    if request.method == 'GET':
        bookstore = request.args.get('bookstore')
        date = request.args.get('date')
        if not bookstore or not date:
            return jsonify({"error": "Missing required parameters"}), 400
        
        # DynamoDB에서 예약 조회
        result = query_reservations(bookstore, date)
        if isinstance(result, str):  # 오류 메시지 처리
            return jsonify({"error": result}), 500
        return jsonify(result), 200

    elif request.method == 'POST':
        try:
            # 요청 바디에서 JSON 데이터 가져오기
            data = request.get_json()
            bookstore = data['bookstore']
            date = data['date']
            time = data['time']
            customer = data['customer']
        except KeyError as e:
            return jsonify({"error": f"Missing key: {str(e)}"}), 400

        # DynamoDB에 예약 생성
        result = create_reservation(bookstore, date, time, customer)
        if isinstance(result, str):  # 오류 메시지 처리
            return jsonify({"error": result}), 500

        # 예약 생성 후 이메일 전송
        sns_result = send_sns_email(bookstore, date, time, customer)
        if isinstance(sns_result, str):  # 오류 메시지 처리
            return jsonify({"error": sns_result}), 500

        return jsonify({"message": "Reservation created successfully, email notification sent"}), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

