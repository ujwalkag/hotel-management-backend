# utils/oracle_storage.py

import oci
import base64
import os

ORACLE_REGION = os.getenv('ORACLE_REGION')
ORACLE_BUCKET_NAME = os.getenv('ORACLE_BUCKET_NAME')
ORACLE_NAMESPACE = 'your_namespace'  # Replace this with actual Oracle namespace (you can find it in bucket details)

config = {
    "user": os.getenv("ORACLE_ACCESS_KEY"),
    "fingerprint": "N/A",
    "tenancy": "N/A",
    "region": ORACLE_REGION,
    "key_content": os.getenv("ORACLE_SECRET_KEY"),
}

# OCI Identity Client requires more details if you're using API Key. For auth tokens (recommended for Object Storage),
# you can simplify using resource principal or generate a signer manually

signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()

object_storage_client = oci.object_storage.ObjectStorageClient({}, signer=signer)


def upload_file_to_oracle(file, object_name):
    try:
        response = object_storage_client.put_object(
            namespace_name=ORACLE_NAMESPACE,
            bucket_name=ORACLE_BUCKET_NAME,
            object_name=object_name,
            put_object_body=file,
        )
        return f"https://objectstorage.{ORACLE_REGION}.oraclecloud.com/n/{ORACLE_NAMESPACE}/b/{ORACLE_BUCKET_NAME}/o/{object_name}"
    except Exception as e:
        print("Upload failed:", str(e))
        return None

