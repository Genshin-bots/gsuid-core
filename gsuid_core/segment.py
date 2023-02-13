from io import BytesIO
from base64 import b64encode
from typing import List, Union

from PIL import Image
from model import Message


class MessageSegment:
    def __add__(self, other):
        return [self, other]

    @staticmethod
    def image(img: Union[str, Image.Image, bytes]) -> Message:
        if isinstance(img, Image.Image):
            img = img.convert('RGB')
            result_buffer = BytesIO()
            img.save(result_buffer, format='PNG', quality=80, subsampling=0)
            img = result_buffer.getvalue()
        elif isinstance(img, bytes):
            pass
        else:
            with open(img, 'rb') as fp:
                img = fp.read()
        msg = Message(type='image', data=f'base64://{b64encode(img).decode()}')
        return msg

    @staticmethod
    def text(content: str) -> Message:
        return Message(type='text', data=content)

    @staticmethod
    def at(user: str) -> Message:
        return Message(type='at', data=user)

    @staticmethod
    def node(content_list: List[Message]) -> Message:
        return Message(type='node', data=content_list)

    @staticmethod
    def record(content: str) -> Message:
        return Message(type='recor', data=content)
