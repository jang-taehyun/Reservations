from flask import Flask, request, jsonify
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta
import time

app = Flask(__name__)

# DynamoDB 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')
table = dynamodb.Table('Reservations')
bookstore_table = dynamodb.Table('BookstoreEmails')  # 서점 이메일 테이블

# SES 클라이언트 초기화
ses_client = boto3.client('ses', region_name='ap-northeast-2')

def get_current_timestamp():
    return int(time.time())

def get_next_reservation_id(bookstore):
    try:
        # 가장 큰 ReservationID를 찾아 다음 ID를 계산
        response = table.query(
            KeyConditionExpression=Key('BookstoreName').eq(bookstore),
            ProjectionExpression="ReservationID",
            ScanIndexForward=False,  # 내림차순으로 조회
            Limit=1  # 가장 큰 ReservationID 하나만 가져옴
        )
        items = response.get('Items', [])
        if items:
            return items[0]['ReservationID'] + 1
        else:
            return 1  # 첫 예약이라면 ReservationID는 1로 시작
    except (BotoCoreError, ClientError) as e:
        return str(e)

def query_reservations(bookstore, date, time_slot):
    try:
        # DynamoDB에서 같은 서점, 날짜, 시간에 예약이 있는지 확인
        response = table.scan(
            FilterExpression=Key('BookstoreName').eq(bookstore) & Key('Date').eq(date) & Key('Time').eq(time_slot)
        )
        return response.get('Items', [])
    except (BotoCoreError, ClientError) as e:
        return str(e)
    
def create_reservation(bookstore, date, time_slot, customer, timestamp):
    # 먼저 예약 중복 확인
    existing_reservations = query_reservations(bookstore, date, time_slot)
    if existing_reservations:
        return "Error: Reservation already exists for this time."

    # 다음 ReservationID를 가져옴
    reservation_id = get_next_reservation_id(bookstore)
    if isinstance(reservation_id, str):  # 오류 발생 시
        return reservation_id

    try:
        # 중복이 없을 경우 새로 예약 생성
        response = table.put_item(
            Item={
                'BookstoreName': bookstore,
                'ReservationID': reservation_id,
                'Date': date,
                'Time': time_slot,
                'Customer': customer,
                'Timestamp': timestamp
            }
        )
        return response
    except ClientError as e:
        return str(e)

def get_email_from_bookstore(bookstore):
    try:
        response = bookstore_table.get_item(
            Key={'BookstoreName': bookstore}
        )
        return response['Item']['Email'] if 'Item' in response else None
    except (BotoCoreError, ClientError) as e:
        return str(e)

def send_ses_email(bookstore, date, time, customer, timestamp):
    try:
        # Bookstore 이름으로 이메일 주소 조회
        email = get_email_from_bookstore(bookstore)
        if not email:
            return f"No email found for bookstore: {bookstore}"
        
        # SES 이메일 전송
        response = ses_client.send_email(
            Source='jth0202@naver.com',  # SES에서 인증된 이메일 주소로 변경
            Destination={
                'ToAddresses': [email],
            },
            Message={
                'Subject': {
                    'Data': 'New Reservation Created (Bookstore CEO)',
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': f"New reservation created:\n\nBookstore: {bookstore}\nDate: {date}\nTime: {time}\nCustomer: {customer}\nReservation Time: {timestamp}",
                        'Charset': 'UTF-8'
                    }
                }
            }
        )

        response = ses_client.send_email(
            Source='jth0202@naver.com',  # SES에서 인증된 이메일 주소로 변경
            Destination={
                'ToAddresses': [customer],
            },
            Message={
                'Subject': {
                    'Data': 'New Reservation Created (Customer)',
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': f"New reservation created:\n\nBookstore: {bookstore}\nDate: {date}\nTime: {time}\nCustomer: {customer}\nReservation Time: {timestamp}",
                        'Charset': 'UTF-8'
                    }
                }
            }
        )

        return response
    except (BotoCoreError, ClientError) as e:
        return str(e)
    
def generate_time_slots(reservations):
    # 09:00부터 18:00까지 1시간 단위로 시간대를 생성
    start_time = datetime.strptime("09:00", "%H:%M")
    time_slots = []
    
    for i in range(10):  # 09:00부터 18:00까지 10개의 슬롯
        time_str = (start_time + timedelta(hours=i)).strftime("%H:%M")
        
        # 해당 시간에 예약이 있는지 확인
        is_reserved = any(reservation['Time'] == time_str for reservation in reservations)
        
        # 예약이 있으면 true, 예약이 없으면 false
        time_slots.append({
            "time": time_str,
            "isReservation": is_reserved
        })
    
    return time_slots

@app.route('/reservations', methods=['GET', 'POST'])
def reservations():
    if request.method == 'GET':
        bookstore = request.args.get('bookstore')
        date = request.args.get('date')
        if not bookstore or not date:
            return jsonify({"error": "Missing required parameters"}), 400

        # DynamoDB에서 해당 서점 및 날짜에 예약된 항목 조회
        try:
            response = table.scan(
                FilterExpression=Key('BookstoreName').eq(bookstore) & Key('Date').eq(date)
            )
            items = response.get('Items', [])
            
            # 예약된 항목을 기반으로 시간대 및 예약 여부 생성
            time_slots = generate_time_slots(items)

            return jsonify(time_slots), 200
        except (BotoCoreError, ClientError) as e:
            return jsonify({"error": str(e)}), 500 

    elif request.method == 'POST':
        try:
            # 요청 바디에서 JSON 데이터 가져오기
            data = request.get_json()
            bookstore = data['bookstore']
            date = data['date']
            time = data['time']
            customer = data['customer']
            timestamp = get_current_timestamp()
        except KeyError as e:
            return jsonify({"error": f"Missing key: {str(e)}"}), 400

        # DynamoDB에 예약 생성
        result = create_reservation(bookstore, date, time, customer, timestamp)
        if isinstance(result, str):  # 오류 메시지 처리
            return jsonify({"error": result}), 500

        # 예약 생성 후 SES를 통해 이메일 알림 전송
        ses_result = send_ses_email(bookstore, date, time, customer, timestamp)
        if isinstance(ses_result, str):  # 오류 메시지 처리
            return jsonify({"error": ses_result}), 500

        return jsonify({"message": "Reservation created successfully, email notification sent"}), 201

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "message": "The reservation application is running normally"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
