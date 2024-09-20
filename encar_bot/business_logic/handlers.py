from logging import Handler
import json


class DBHandler(Handler, object):
    model_name = None
    expiry = None

    def __init__(self, model="", expiry=0):
        super(DBHandler, self).__init__()
        self.model_name = model
        self.expiry = int(expiry)

    def emit(self, record):
        try:
            try:
                model = self.get_model(self.model_name)
            except:
                from models import DBLog as model

            log_entry = model(level=record.levelname, message=self.format(record), filename=record.filename,
                              func_name=record.funcName, lineno=record.lineno)

            try:
                data = json.loads(record.msg)
                for key, value in data.items():
                    if hasattr(log_entry, key):
                        try:
                            setattr(log_entry, key, value)
                        except:
                            pass
            except:
                pass
            log_entry.save()
        except:
            pass

    def get_model(self, name):
        names = name.split('.')
        mod = __import__('.'.join(names[:-1]), fromlist=names[-1:])
        return getattr(mod, names[-1])
