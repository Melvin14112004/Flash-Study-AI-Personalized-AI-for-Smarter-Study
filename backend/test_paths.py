import os
from config import LOCAL_MODELS_DIR

print("LOCAL_MODELS_DIR =", LOCAL_MODELS_DIR)
print("Exists?", os.path.exists(LOCAL_MODELS_DIR))

led = os.path.join(LOCAL_MODELS_DIR, "led-base-16384")
print("LED path =", led)
print("LED exists?", os.path.exists(led))

t5 = os.path.join(LOCAL_MODELS_DIR, "t5-small")
print("T5 path =", t5)
print("T5 exists?", os.path.exists(t5))
