
import zlib
import hashlib
import base64
import boto3
import os
from .config import Config


def to_unicode(data):
    try:
        return str(data, 'utf-8')
    except:
        pass
    return data


class DataZipper(object):

    s3 = boto3.resource('s3')
    bucket = Config.zipper_bucket
    path = '/'.join(Config.zipper_path.split('/')[1:])
    magick_zip = "FF-ZIP"
    magick_url = "FF-URL"
    separator = ":"

    @classmethod
    def _make_key(cls, filename):
        return os.path.join(cls.path, filename)

    @classmethod
    def deliver(cls, data, limit):
        if len(data) < limit:
            return data

        zipped = cls._zip_data(data, limit)

        if len(zipped) > limit:
            # Even zipped it was too big! Let's stick it on S3.
            return cls._store_in_s3(zipped)
        else:
            return zipped

    @classmethod
    def _zip_data(cls, data, limit):
        the_bytes = to_unicode(data)
        zipped = zlib.compress(the_bytes.encode('utf-8'))

        return cls.separator.join((cls.magick_zip, str(len(the_bytes)), to_unicode(base64.b64encode(zipped))))

    @classmethod
    def _store_in_s3(cls, data):
        md5 = hashlib.md5()
        result_bytes = to_unicode(data)
        md5.update(result_bytes.encode('utf-8'))
        md5_hash = md5.hexdigest()

        s3_key = cls._make_key(md5_hash + ".ff")

        s3_obj = cls.s3.Object(cls.bucket, s3_key)
        s3_obj.put(Body=result_bytes)

        return cls.separator.join((cls.magick_url, md5_hash, "s3://{}/{}".format(cls.bucket, s3_key)))

    @classmethod
    def receive(cls, data):
        if data.startswith(cls.magick_zip):
            return cls._receive_zipped(data)
        elif data.startswith(cls.magick_url):
            return cls._receive_url(data)
        else:
            return data

    @classmethod
    def _receive_url(cls, ff_url):
        # sample ff url:
        # FF-URL:ca5c3877664255d120079fa323850b7f:s3://balihoo.dev.fulfillment/retain_30_180/zipped-ff/ca5c3877664255d120079fa323850b7f.ff
        s, h, proto, path = ff_url.split(cls.separator)
        path_parts = list(filter(len, path.split('/')))
        bucket = path_parts[0]
        key = '/'.join(path_parts[1:])
        assert proto == "s3", "DataZipper only supports s3 protocol for fulfillment documents"

        s3_obj = cls.s3.Object(bucket, key)
        response = s3_obj.get()

        return cls.receive(response['Body'].read())

    @classmethod
    def _receive_zipped(cls, zipped):
        # 17 chars allows for a 10 digit length!
        s, length_string, head = zipped[:min(17, len(zipped))].split(cls.separator)
        # parts would look like ("FF-ZIP", "56794", "blah blah blah...")
        header_length = len(cls.magick_zip) + len(length_string) + 2  # 2 separators

        return zlib.decompress(base64.b64decode(zipped[header_length:])).decode('utf-8')

