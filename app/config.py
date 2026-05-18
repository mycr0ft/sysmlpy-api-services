import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "sysmlv2-dev-secret-key")
    JSON_SORT_KEYS = False
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
