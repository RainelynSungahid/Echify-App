from src.gesture.fsl_dynamic_inference import initialize_dynamic_model, get_model_info
from session_logger import global_logger
initialize_dynamic_model()
print("model ok")
global_logger.log_reconnect("Sign-TTS", "test")
print("logger ok")
