"""
Model optimization utilities for deployment.
Compress and optimize ML models for cloud hosting with size/memory constraints.
"""
import os
import joblib
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def get_model_size_mb(model_path: str) -> float:
    """Get model file size in MB"""
    if os.path.exists(model_path):
        size_bytes = os.path.getsize(model_path)
        return size_bytes / (1024 * 1024)
    return 0.0


def compress_sklearn_model(model_path: str, output_path: Optional[str] = None, compress_level: int = 9) -> str:
    """
    Compress scikit-learn models using joblib compression.
    
    Args:
        model_path: Path to the model file
        output_path: Optional output path (defaults to same path with .compressed)
        compress_level: Compression level 0-9 (9 = maximum)
    
    Returns:
        Path to compressed model
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    if output_path is None:
        output_path = model_path.replace('.pkl', '.compressed.pkl')
    
    try:
        # Load model
        model = joblib.load(model_path)
        
        # Save with compression
        joblib.dump(model, output_path, compress=compress_level)
        
        original_size = get_model_size_mb(model_path)
        compressed_size = get_model_size_mb(output_path)
        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        
        logger.info(
            f"Compressed {model_path}: {original_size:.2f}MB -> {compressed_size:.2f}MB "
            f"({compression_ratio:.1f}% reduction)"
        )
        
        return output_path
    except Exception as e:
        logger.error(f"Failed to compress model {model_path}: {e}")
        raise


def quantize_tensorflow_model(model_path: str, output_path: Optional[str] = None) -> str:
    """
    Quantize TensorFlow/Keras models to reduce size.
    
    Args:
        model_path: Path to the .keras or .h5 model
        output_path: Optional output path
    
    Returns:
        Path to quantized model
    """
    try:
        import tensorflow as tf
    except ImportError:
        logger.warning("TensorFlow not installed, skipping quantization")
        return model_path
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    if output_path is None:
        base, ext = os.path.splitext(model_path)
        output_path = f"{base}.quantized{ext}"
    
    try:
        # Load model
        model = tf.keras.models.load_model(model_path)
        
        # Convert to TFLite with quantization
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        
        # Post-training quantization
        tflite_model = converter.convert()
        
        # Save quantized model
        tflite_path = output_path.replace('.keras', '.tflite').replace('.h5', '.tflite')
        with open(tflite_path, 'wb') as f:
            f.write(tflite_model)
        
        original_size = get_model_size_mb(model_path)
        quantized_size = get_model_size_mb(tflite_path)
        compression_ratio = (1 - quantized_size / original_size) * 100 if original_size > 0 else 0
        
        logger.info(
            f"Quantized {model_path}: {original_size:.2f}MB -> {quantized_size:.2f}MB "
            f"({compression_ratio:.1f}% reduction)"
        )
        
        return tflite_path
    except Exception as e:
        logger.error(f"Failed to quantize model {model_path}: {e}")
        raise


def optimize_pytorch_model(model_path: str, output_path: Optional[str] = None) -> str:
    """
    Optimize PyTorch models for inference.
    
    Args:
        model_path: Path to the .pt or .pth model
        output_path: Optional output path
    
    Returns:
        Path to optimized model
    """
    try:
        import torch
    except ImportError:
        logger.warning("PyTorch not installed, skipping optimization")
        return model_path
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    if output_path is None:
        base, ext = os.path.splitext(model_path)
        output_path = f"{base}.optimized{ext}"
    
    try:
        # Load model
        model = torch.load(model_path, map_location='cpu')
        
        # Set to eval mode
        if hasattr(model, 'eval'):
            model.eval()
        
        # Save with optimization
        torch.save(model, output_path, _use_new_zipfile_serialization=True)
        
        original_size = get_model_size_mb(model_path)
        optimized_size = get_model_size_mb(output_path)
        
        logger.info(
            f"Optimized {model_path}: {original_size:.2f}MB -> {optimized_size:.2f}MB"
        )
        
        return output_path
    except Exception as e:
        logger.error(f"Failed to optimize PyTorch model {model_path}: {e}")
        raise


def optimize_all_models(models_dir: str = "backend/models", max_size_mb: float = 100.0) -> Dict[str, Any]:
    """
    Optimize all models in the models directory.
    
    Args:
        models_dir: Directory containing models
        max_size_mb: Maximum allowed model size (Railway free tier ~500MB total)
    
    Returns:
        Dictionary with optimization results
    """
    models_path = Path(models_dir)
    if not models_path.exists():
        logger.warning(f"Models directory not found: {models_dir}")
        return {"status": "error", "message": "Models directory not found"}
    
    results = {
        "optimized": [],
        "skipped": [],
        "errors": [],
        "total_size_before_mb": 0.0,
        "total_size_after_mb": 0.0
    }
    
    # Find all model files
    model_files = []
    model_files.extend(models_path.glob("*.pkl"))
    model_files.extend(models_path.glob("*.keras"))
    model_files.extend(models_path.glob("*.h5"))
    model_files.extend(models_path.glob("*.pt"))
    model_files.extend(models_path.glob("*.pth"))
    
    for model_file in model_files:
        model_path = str(model_file)
        size_mb = get_model_size_mb(model_path)
        results["total_size_before_mb"] += size_mb
        
        # Skip if already optimized
        if any(x in model_path for x in ['.compressed', '.quantized', '.optimized']):
            results["skipped"].append({
                "path": model_path,
                "reason": "Already optimized",
                "size_mb": size_mb
            })
            results["total_size_after_mb"] += size_mb
            continue
        
        try:
            if model_path.endswith('.pkl'):
                optimized_path = compress_sklearn_model(model_path)
                optimized_size = get_model_size_mb(optimized_path)
                results["optimized"].append({
                    "original": model_path,
                    "optimized": optimized_path,
                    "size_before_mb": size_mb,
                    "size_after_mb": optimized_size
                })
                results["total_size_after_mb"] += optimized_size
                
            elif model_path.endswith(('.keras', '.h5')):
                optimized_path = quantize_tensorflow_model(model_path)
                optimized_size = get_model_size_mb(optimized_path)
                results["optimized"].append({
                    "original": model_path,
                    "optimized": optimized_path,
                    "size_before_mb": size_mb,
                    "size_after_mb": optimized_size
                })
                results["total_size_after_mb"] += optimized_size
                
            elif model_path.endswith(('.pt', '.pth')):
                optimized_path = optimize_pytorch_model(model_path)
                optimized_size = get_model_size_mb(optimized_path)
                results["optimized"].append({
                    "original": model_path,
                    "optimized": optimized_path,
                    "size_before_mb": size_mb,
                    "size_after_mb": optimized_size
                })
                results["total_size_after_mb"] += optimized_size
                
        except Exception as e:
            results["errors"].append({
                "path": model_path,
                "error": str(e)
            })
            # Keep original size in total
            results["total_size_after_mb"] += size_mb
    
    # Calculate overall compression
    if results["total_size_before_mb"] > 0:
        compression_ratio = (1 - results["total_size_after_mb"] / results["total_size_before_mb"]) * 100
        results["compression_ratio_pct"] = compression_ratio
    else:
        results["compression_ratio_pct"] = 0.0
    
    # Check if total size exceeds limit
    results["within_limit"] = results["total_size_after_mb"] <= max_size_mb
    results["max_size_mb"] = max_size_mb
    
    logger.info(
        f"Model optimization complete: {results['total_size_before_mb']:.2f}MB -> "
        f"{results['total_size_after_mb']:.2f}MB ({results['compression_ratio_pct']:.1f}% reduction)"
    )
    
    if not results["within_limit"]:
        logger.warning(
            f"Total model size ({results['total_size_after_mb']:.2f}MB) exceeds "
            f"limit ({max_size_mb}MB). Consider removing unused models."
        )
    
    return results


if __name__ == "__main__":
    # Run optimization
    logging.basicConfig(level=logging.INFO)
    results = optimize_all_models()
    
    print("\n" + "="*60)
    print("MODEL OPTIMIZATION RESULTS")
    print("="*60)
    print(f"Total size before: {results['total_size_before_mb']:.2f} MB")
    print(f"Total size after:  {results['total_size_after_mb']:.2f} MB")
    print(f"Compression ratio: {results['compression_ratio_pct']:.1f}%")
    print(f"Within limit ({results['max_size_mb']}MB): {results['within_limit']}")
    print(f"\nOptimized: {len(results['optimized'])} models")
    print(f"Skipped:   {len(results['skipped'])} models")
    print(f"Errors:    {len(results['errors'])} models")
    print("="*60)

