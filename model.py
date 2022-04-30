import os
import traceback

from framework import app, db, path_data
from framework.logger import get_logger
from framework.util import Util

package_name = __name__.split(".", maxsplit=1)[0]
logger = get_logger(package_name)
app.config["SQLALCHEMY_BINDS"][package_name] = "sqlite:///%s" % (
    os.path.join(path_data, "db", f"{package_name}.db")
)


class ModelSetting(db.Model):
    __tablename__ = f"{package_name}_setting"
    __table_args__ = {"mysql_collate": "utf8_general_ci"}
    __bind_key__ = package_name

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String, nullable=False)

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return repr(self.as_dict())

    def as_dict(self):
        return {x.name: getattr(self, x.name) for x in self.__table__.columns}

    @staticmethod
    def get(key):
        try:
            return (
                db.session.query(ModelSetting).filter_by(key=key).first().value.strip()
            )
        except Exception as e:
            logger.error("Exception:%s %s", e, key)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_int(key):
        try:
            return int(ModelSetting.get(key))
        except Exception as e:
            logger.error("Exception:%s %s", e, key)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_bool(key):
        try:
            return ModelSetting.get(key) == "True"
        except Exception as e:
            logger.error("Exception:%s %s", e, key)
            logger.error(traceback.format_exc())

    @staticmethod
    def set(key, value):
        try:
            item = (
                db.session.query(ModelSetting)
                .filter_by(key=key)
                .with_for_update()
                .first()
            )
            if item is not None:
                item.value = value.strip()
                db.session.commit()
            else:
                db.session.add(ModelSetting(key, value.strip()))
        except Exception as e:
            logger.error("Exception:%s", e)
            logger.error(traceback.format_exc())
            logger.error("Error Key:%s Value:%s", key, value)

    @staticmethod
    def to_dict():
        try:
            return Util.db_list_to_dict(db.session.query(ModelSetting).all())
        except Exception as e:
            logger.error("Exception:%s", e)
            logger.error(traceback.format_exc())

    @staticmethod
    def setting_save(req):
        try:
            for key, value in req.form.items():
                if key in ["scheduler", "is_running"]:
                    continue
                if key.startswith("tmp_"):
                    continue
                logger.debug("Key:%s Value:%s", key, value)
                entity = (
                    db.session.query(ModelSetting)
                    .filter_by(key=key)
                    .with_for_update()
                    .first()
                )
                entity.value = value
            db.session.commit()
            return True
        except Exception as e:
            logger.error("Exception:%s", e)
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def get_list(key):
        try:
            value = ModelSetting.get(key)
            values = [x.strip().strip() for x in value.replace("\n", "|").split("|")]
            values = Util.get_list_except_empty(values)
            return values
        except Exception as e:
            logger.error("Exception:%s %s", e, key)
            logger.error(traceback.format_exc())
