import logging


class CommaMillisecondFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        import datetime
        ct = datetime.datetime.fromtimestamp(record.created)
        return ct.strftime("%d-%m-%Y %H:%M:%S,") + f"{int(record.msecs):03d}"


handler = logging.StreamHandler()
handler.setFormatter(CommaMillisecondFormatter(
    fmt="[%(asctime)s  %(levelname)s %(name)s:0] %(message)s"
))

logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger(__name__)