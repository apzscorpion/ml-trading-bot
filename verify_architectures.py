
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

try:
    from backend.bots.lstm_bot import LSTMBot
    from backend.bots.transformer_bot import TransformerBot
    
    print("Initializing LSTM Bot...")
    lstm = LSTMBot()
    if lstm.model:
        print("\nLSTM Model Summary:")
        lstm.model.summary()
    else:
        print("LSTM Model not created (TensorFlow missing?)")
        
    print("\n" + "="*50 + "\n")
    
    print("Initializing Transformer Bot...")
    transformer = TransformerBot()
    if transformer.model:
        print("\nTransformer Model Summary:")
        transformer.model.summary()
    else:
        print("Transformer Model not created (TensorFlow missing?)")

except Exception as e:
    print(f"Error: {e}")
