import logging

logger = logging.getLogger(__name__)
logger.debug("Initializing services package")

from .training_service import TrainingService
