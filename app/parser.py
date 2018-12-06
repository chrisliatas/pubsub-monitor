import logging
import json

logger = logging.getLogger()


class MsgParser:
    def __init__(self, message):
        self.msg = message
        self.msg_id = message.message_id
        self.msg_publish_time = message.publish_time
        self._rdata = message.data
        self._rmsg_attrs = message.attributes
        logger.info('Parsing received message {}'.format(self.msg_id))
        self.data = self._to_json()
        self.msg_attrs = self._to_json(True)

    def _to_json(self, is_attrs=False):
        try:
            data = ({k: self._rmsg_attrs.get(k) for k in self._rmsg_attrs} if self._rmsg_attrs else {}
                    ) if is_attrs else self._rdata.decode('utf-8')
            # `message.data` is a JSON formatted string
            return json.dumps(data) if is_attrs else data
        except Exception as e:
            logger.error('[MsgParser._to_json] - Message: {}\nException thrown: {}.'.format(self.msg, e))
            return {}
