import logging

logger = logging.getLogger(__name__)
logger.debug("Initializing services package")

from app.services.training_service import Training
