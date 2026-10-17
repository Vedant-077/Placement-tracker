"""File storage: uses AWS S3 if S3_BUCKET is set, otherwise the local 'uploads' folder."""
import os
import uuid
from werkzeug.utils import secure_filename

S3_BUCKET = os.environ.get("S3_BUCKET")
LOCAL_DIR = os.environ.get("UPLOAD_DIR", "uploads")


def _s3():
    import boto3  # imported here so local runs don't need AWS
    return boto3.client("s3", region_name=os.environ.get("AWS_REGION", "ap-south-1"))


def save_file(file_obj):
    """Saves the file and returns a key (its stored name)."""
    key = f"{uuid.uuid4().hex}_{secure_filename(file_obj.filename)}"
    if S3_BUCKET:
        _s3().upload_fileobj(file_obj, S3_BUCKET, key)
    else:
        os.makedirs(LOCAL_DIR, exist_ok=True)
        file_obj.save(os.path.join(LOCAL_DIR, key))
    return key


def get_download_url(key, local_route):
    """Returns a link the user can click to download the file."""
    if S3_BUCKET:
        return _s3().generate_presigned_url(
            "get_object", Params={"Bucket": S3_BUCKET, "Key": key}, ExpiresIn=300
        )
    return local_route
