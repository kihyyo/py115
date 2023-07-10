__author__ = 'deadblue'

from datetime import datetime
from enum import IntEnum

from py115._internal import oss, utils


class LoginPlatform(IntEnum):
    Web = 0
    """Login as web"""
    Mac = 1
    """Login as MAC app"""
    Linux = 2
    """Login as Linux app"""
    Windows = 3
    """Login as Windows app"""


class _Base:
    """Base clase for all types."""

    def __repr__(self) -> str:
        cls_name = type(self).__name__
        attrs = ', '.join([
            f'{k}={v}' for k, v in self.__dict__.items()
        ])
        return f'{cls_name}({attrs})'


class Credential(_Base):
    """Credential contains required information to identify user.

    Args:
        uid (str): The "UID" value in cookies.
        cid (str): The "CID" value in cookies.
        seid (str): The "SEID" value in cookies.
    """

    _uid: str = None
    _cid: str = None
    _seid: str = None

    def __init__(self, uid: str = None, cid: str = None, seid: str = None) -> None:
        self._uid = uid
        self._cid = cid
        self._seid = seid

    @classmethod
    def from_dict(cls, d: dict):
        """Create Credential from a dict object.

        Args:
            d (dict): Dict object.

        Returns:
            py115.types.Credential: Credential object.
        """
        if len(d) == 0 or not ('UID' in d and 'CID' in d and 'SEID' in d):
            return None
        return Credential(
            uid=d.get('UID'),
            cid=d.get('CID'),
            seid=d.get('SEID')
        )

    def to_dict(self) -> dict:
        """Convert credential object to dict object.

        Returns:
            dict: Dict object.
        """
        return {
            'UID': self._uid,
            'CID': self._cid,
            'SEID': self._seid,
        }


class File(_Base):
    """File represents a cloud file or directory."""

    file_id: str
    """Unique ID of the file on cloud."""

    parent_id: str
    """File ID of the parent directory."""

    name: str
    """Base name."""

    size: int
    """Size in bytes."""

    modified_time: datetime
    """Last modified datetime."""

    sha1: str
    """SHA-1 hash of the file in HEX encoding."""

    pickcode: str
    """Pickcode to download the file."""

    is_dir: bool
    """Is file a directory."""

    @classmethod
    def _create(cls, raw: dict):
        category_id = raw.get('cid')
        file_id = raw.get('fid')
        parent_id = raw.get('pid')

        r = cls()
        r.is_dir = file_id is None
        r.name = raw.get('n')
        if 'te' in raw:
            r.modified_time = utils.parse_datetime_str(raw.get('te'))
        else:
            r.modified_time = utils.parse_datetime_str(raw.get('t'))
        if r.is_dir:
            r.file_id = category_id
            r.parent_id = parent_id
            r.size, r.sha1, r.pickcode = 0, None, None
        else:
            r.file_id = file_id
            r.parent_id = category_id
            r.size = raw.get('s')
            r.sha1 = raw.get('sha')
            r.pickcode = raw.get('pc')
        return r

    def __str__(self) -> str:
        if self.is_dir:
            return f'{self.name}/'
        else:
            return self.name


class DownloadTicket(_Base):
    """
    DownloadTicket contains required parameters to download a file from 
    cloud storage.

    Please check examples for detail usage.
    """

    file_name: str
    """Base name of the file."""

    file_size: int
    """Size of the file."""

    url: str
    """Download URL."""

    headers: dict
    """Required headers that should be used with download URL."""


class PlayTicket(_Base):

    url: str
    """Download URL."""

    headers: dict
    """Required headers that should be used with download URL."""


class UploadTicket(_Base):
    """
    UploadTicket contains required parameters to upload a file to 
    cloud storage.

    Please check examples for detial usage.
    """

    is_done: bool
    """Is file already uploaded."""

    oss_endpoint: str
    """OSS endpoint address."""

    oss_token: dict
    """OSS token"""

    bucket_name: str
    """OSS bucket name."""

    object_key: str
    """OSS object key."""

    headers: dict
    """Required headers that should be used in upload."""

    expiration: datetime
    """Expiration time of this ticket."""

    @classmethod
    def _create(cls, raw: dict, token: dict):
        r = cls()
        r.is_done = raw['done']
        if not r.is_done:
            r.oss_endpoint = oss.ENDPOINT
            r.oss_token = {
                'access_key_id': token.get('access_key_id'),
                'access_key_secret': token.get('access_key_secret'),
                'security_token': token.get('security_token')
            }
            r.bucket_name = raw.get('bucket')
            r.object_key = raw.get('object')
            r.headers = {
                'x-oss-callback': oss.encode_header_value(raw.get('callback')),
                'x-oss-callback-var': oss.encode_header_value(raw.get('callback_var'))
            }
            r.expiration = token.get('expiration')
        return r
    
    def is_valid(self) -> bool:
        """Check whether the ticket is valid.

        Returns:
            bool: Valid flag.
        """
        return datetime.now() < self.expiration


class TaskStatus(IntEnum):
    Running = 1
    """Task is running."""
    Complete = 2
    """Task is complete."""
    Failed = -1
    """Task is failed."""
    Unknown = 0
    """Unknown status?"""


class Task(_Base):
    """Task represents an offline task."""

    task_id: str
    """Unique ID of the task."""

    name: str
    """Task name."""

    size: int
    """Total size to be downloaded."""

    created_time: datetime
    """Task created time."""

    percent: float
    """Precentage of the download, 0~100."""

    file_id: str
    """Downloaded file ID of the task, may be None if the task does not finish."""

    file_is_dir: bool
    """Is the downloaded file a directory."""

    status: TaskStatus
    """Task status."""

    @classmethod
    def _create(cls, raw: dict):
        r = cls()
        r.task_id = raw.get('info_hash')
        r.name = raw.get('name')
        r.size = raw.get('size', -1)
        r.created_time = utils.make_datetime(raw.get('add_time', 0))
        r.precent = float(raw.get('percentDone', 0))
        r.status = TaskStatus(raw.get('status', 0))

        file_id = raw.get('file_id', '')
        del_file_id = raw.get('delete_file_id', '')
        r.file_id = del_file_id
        r.file_is_dir = file_id != '' and file_id == del_file_id
        return r

    def is_complete(self) -> bool:
        """Check is task complete."""
        return self.status == TaskStatus.Complete

    def is_failed(self) -> bool:
        """Check is task failed."""
        return self.status == TaskStatus.Failed

    def is_running(self) -> bool:
        """Check is task still running."""
        return self.status == TaskStatus.Running