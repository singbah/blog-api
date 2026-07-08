import boto3
import os
from uuid import uuid4
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()


R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET = os.getenv("R2_BUCKET")
R2_ENDPOINT = os.getenv("R2_ENDPOINT_URL")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL")


s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)

    

def upload_to_r2(file, folder="posts"):
    """
    Upload file to Cloudflare R2 and return public URL
    """

    file_extension = file.filename.split(".")[-1]
    filename = f"{folder}/{uuid4().hex}.{file_extension}"

    file.file.seek(0)
    file_data = file.file.read()

    s3.put_object(
        Bucket=R2_BUCKET,
        Key=filename,
        Body=file_data,
        ContentType=file.content_type,
    )

    public_url = f"{R2_PUBLIC_URL}/{filename}"

    return {
        "key": filename,
        "url": public_url
    }
    
def delete_file_from_r2(file_key: str):
    """
    Delete a file from Cloudflare R2 using its object key
    """
    try:
        if not file_key:
            return False

        s3.delete_object(
            Bucket=R2_BUCKET,
            Key=file_key
        )

        print(f"{file_key} deleted from R2")
        return True

    except Exception as e:
        print("R2 delete error:", e)
        raise