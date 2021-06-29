# -*- coding: utf-8 -*-
import logging.config
import os

from src.util import get_root_path, read_yaml

log_config_path = os.path.join(get_root_path(), 'src', 'config', 'log_config.yaml')
logging.config.dictConfig(read_yaml(log_config_path))
logger = logging.getLogger(__name__)
