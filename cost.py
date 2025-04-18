import boto3
import datetime
import io
import pandas as pd

def lambda_handler(event, context):
    # AWS 청구서 클라이언트 생성
    client = boto3.client('ce')

    # 검색 기간 설정 (하루 전날)
    end = datetime.datetime.now() - datetime.timedelta(days=1)
    start = end - datetime.timedelta(days=1)

    # AWS 청구서에 요청할 매개변수 생성
    params = {
        'TimePeriod': {
            'Start': start.strftime('%Y-%m-%d'),
            'End': end.strftime('%Y-%m-%d')
        },
        'Granularity': 'DAILY',
        'Metrics': ['UnblendedCost'],
        'GroupBy': [
            {
                'Type': 'DIMENSION',
                'Key': 'SERVICE'  # 서비스별 비용을 가져오기 위한 그룹화 키
            },
            {
                'Type': 'DIMENSION',
                'Key': 'LINKED_ACCOUNT'  # 링크된 어카운트별 비용을 가져오기 위한 그룹화 키
            }
        ]
    }

    # AWS 청구서에 요청하여 결과 가져오기
    response = client.get_cost_and_usage(**params)

    # 결과를 DataFrame으로 변환하기
    data = []
    total_cost = 0.0  # 총합 비용 초기화
    for result_by_time in response['ResultsByTime']:
        date = result_by_time['TimePeriod']['Start']
        for group in result_by_time['Groups']:
            linked_account = group['Keys'][1]  # 링크된 어카운트
            service = group['Keys'][0]
            cost = group['Metrics']['UnblendedCost']['Amount']
            total_cost += float(cost)  # 비용을 누적하여 총합 비용 계산
            data.append([linked_account, date, service, cost])
    df = pd.DataFrame(data, columns=['Linked Account', 'Date', 'Service', 'Cost'])

    # 총합 비용 행 추가
    total_row = [linked_account, date, 'Total', str(total_cost)]
    total_df = pd.DataFrame([total_row], columns=['Linked Account', 'Date', 'Service', 'Cost'])
    df = pd.concat([df, total_df], ignore_index=True)

    # DataFrame을 Excel 파일로 저장하기
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)

    # S3 버킷 객체 전부 삭제
    s3 = boto3.resource('s3')
    bucket_name = 'daily-cost-s3'
    bucket = s3.Bucket(bucket_name)
    for obj in bucket.objects.all():
        obj.delete()


    # Excel 파일을 S3 버킷에 업로드하기
    filename = 'aws_cost_{}.xlsx'.format(datetime.datetime.now().strftime('%Y-%m-%d'))
    s3.Object(bucket_name, filename).put(Body=output.getvalue())