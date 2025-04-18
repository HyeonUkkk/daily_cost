import boto3
import os
import email.mime.multipart
import email.mime.base
from botocore.exceptions import ClientError

# AWS SES 클라이언트 생성
ses = boto3.client('ses')

def lambda_handler(event, context):
    # S3 클라이언트 생성
    s3 = boto3.client('s3')

    # S3 버킷에서 파일 가져오기
    bucket_name = 'daily-cost-s3' #버킷 이름 다르면 바꾸어야 합니다.
    file_name = 'merged_cost.xlsx'
    object = s3.get_object(Bucket=bucket_name, Key=file_name)
    file_content = object['Body'].read()

    # 이메일 메시지 생성
    msg = email.mime.multipart.MIMEMultipart()
    msg['Subject'] = 'Daily-cost' #제목
    msg['From'] = '<보내는 이메일>' #인증 받은 메일만 가능
    msg['To'] = '<받는 이메일>' #인증 받은 메일만 가능

    # 파일 첨부
    attachment = email.mime.base.MIMEBase('application', 'octet-stream')
    attachment.set_payload(file_content)
    email.encoders.encode_base64(attachment)
    attachment.add_header('Content-Disposition', 'attachment', filename=file_name)
    msg.attach(attachment)

    # 이메일 보내기
    try:
        response = ses.send_raw_email(
            Source=msg['From'],
            Destinations=[msg['To']],
            RawMessage={'Data': msg.as_string()}
        )
        print('Email sent')
    except ClientError as e:
        print(e.response['Error']['Message'])

    # S3 버킷 객체 전부 삭제
    s3_resource = boto3.resource('s3')
    bucket = s3_resource.Bucket(bucket_name)
    bucket.objects.delete()