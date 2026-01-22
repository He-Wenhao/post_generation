# -*- coding: utf-8 -*-
"""
Image generation script using Replicate's Flux model.
Generates images from text prompts without training functionality.
"""

import os
import json
from pathlib import Path
from datetime import datetime
import replicate
from typing import Optional, Dict
try:
    import requests
    from PIL import Image
    IMAGE_LIBS_AVAILABLE = True
except ImportError:
    IMAGE_LIBS_AVAILABLE = False
    requests = None
    Image = None


def load_config(config_path: Optional[str] = None) -> Dict:
    """
    Load Replicate configuration from JSON file.
    
    Args:
        config_path: Path to config file. If None, uses .config/replicate_config.json
    
    Returns:
        Dictionary with config values
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid
    """
    if config_path is None:
        # Get the project root (assuming this file is in src/image_generation/)
        project_root = Path(__file__).parent.parent
        config_path = project_root / ".config" / "replicate_config.json"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found at {config_path}. "
            f"Please copy .config/replicate_config.json.example to .config/replicate_config.json "
            f"and fill in your credentials."
        )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    return config


def download_image(url: str, output_dir: Optional[Path] = None, filename: Optional[str] = None) -> Path:
    """
    Download an image from a URL and save it as PNG in the .images folder.
    
    Args:
        url: URL of the image to download
        output_dir: Directory to save the image. If None, uses .images in project root
        filename: Optional filename. If None, generates a timestamp-based name
    
    Returns:
        Path to the saved image file
    
    Raises:
        ImportError: If requests or PIL are not installed
        Exception: If download or conversion fails
    """
    if not IMAGE_LIBS_AVAILABLE:
        raise ImportError(
            "Image download requires 'requests' and 'Pillow' libraries. "
            "Install with: pip install requests Pillow"
        )
    
    # Determine output directory
    if output_dir is None:
        project_root = Path(__file__).parent.parent
        output_dir = project_root / ".images"
    else:
        output_dir = Path(output_dir)
    
    # Create directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename if not provided
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_image_{timestamp}.png"
    
    # Ensure filename ends with .png
    if not filename.endswith('.png'):
        filename = f"{Path(filename).stem}.png"
    
    # Download the image
    print(f"Downloading image from {url}...")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    # Save temporarily to check format
    temp_path = output_dir / f"temp_{filename}"
    with open(temp_path, 'wb') as f:
        f.write(response.content)
    
    # Convert to PNG
    try:
        img = Image.open(temp_path)
        # Convert to RGB if necessary (handles RGBA, etc.)
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = rgb_img
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save as PNG
        output_path = output_dir / filename
        img.save(output_path, 'PNG')
        temp_path.unlink()  # Remove temporary file
    except Exception as e:
        print(f"Warning: Could not convert image to PNG: {e}")
        # Fallback: rename temp file
        output_path = output_dir / filename
        temp_path.rename(output_path)
        print(f"Image saved as-is to {output_path}")
    
    print(f"✓ Image saved to: {output_path}")
    return output_path


def setup_replicate(api_key: Optional[str] = None, config: Optional[Dict] = None):
    """
    Setup Replicate API key.
    
    Args:
        api_key: Replicate API key. If None, will try config file or REPLICATE_API_TOKEN env var.
        config: Optional config dictionary. If provided, will use api_key from config.
    """
    if api_key:
        os.environ["REPLICATE_API_TOKEN"] = api_key
    elif config and config.get("api_key"):
        os.environ["REPLICATE_API_TOKEN"] = config["api_key"]
    elif not os.environ.get("REPLICATE_API_TOKEN"):
        raise ValueError(
            "Replicate API key not found. Please set REPLICATE_API_TOKEN environment variable, "
            "pass api_key parameter, or configure .config/replicate_config.json"
        )


def generate_image(
    prompt: str,
    model: str = "black-forest-labs/flux-dev",
    num_inference_steps: int = 28,
    guidance_scale: float = 7.5,
    model_type: str = "dev",
    api_key: Optional[str] = None,
    config: Optional[Dict] = None,
    download: bool = True,
    output_dir: Optional[Path] = None,
    filename: Optional[str] = None
) -> Dict[str, str]:
    """
    Generate an image from a text prompt using Replicate's Flux model.
    
    Args:
        prompt: Text description of the image to generate
        model: Model identifier. Default is "black-forest-labs/flux-dev" (base model).
               Can also be a fine-tuned model like "username/model-name:version"
        num_inference_steps: Number of inference steps (typically ~30 for "dev" model).
                            Less steps = faster generation but lower quality.
                            For "schnell" model, use 4 steps.
        guidance_scale: How much attention the model pays to the prompt (1-50).
                       Higher values = more adherence to prompt.
        model_type: Type of model to use. "dev" for quality, "schnell" for speed.
        api_key: Optional Replicate API key. If None, uses config or environment variable.
        config: Optional config dictionary. If provided, will use api_key from config.
        download: If True, download the image to .images folder (default: True)
        output_dir: Optional directory to save image. If None, uses .images in project root.
        filename: Optional filename for saved image. If None, generates timestamp-based name.
    
    Returns:
        Dictionary with 'url' (image URL) and optionally 'file_path' (if download=True)
    
    Example:
        >>> result = generate_image("A photo of a dog in a space shuttle")
        >>> print(result['url'])
        >>> print(result.get('file_path'))  # Path to downloaded PNG
    """
    setup_replicate(api_key, config)
    
    input_params = {
        "prompt": prompt,
        "num_inference_steps": num_inference_steps,
        "guidance_scale": guidance_scale,
        "model": model_type,
    }
    
    output = replicate.run(model, input=input_params)
    generated_img_url = str(output[0])
    
    result = {"url": generated_img_url}
    
    # Download image if requested
    if download:
        try:
            file_path = download_image(generated_img_url, output_dir, filename)
            result["file_path"] = str(file_path)
        except Exception as e:
            print(f"Warning: Failed to download image: {e}")
            print(f"Image URL: {generated_img_url}")
    
    return result


def generate_image_finetuned(
    prompt: str,
    model_owner: str,
    model_name: str,
    trigger_word: Optional[str] = None,
    num_inference_steps: int = 28,
    guidance_scale: float = 7.5,
    model_type: str = "dev",
    api_key: Optional[str] = None,
    config: Optional[Dict] = None,
    download: bool = True,
    output_dir: Optional[Path] = None,
    filename: Optional[str] = None
) -> Dict[str, str]:
    """
    Generate an image using a fine-tuned model.
    
    Args:
        prompt: Text description of the image to generate
        model_owner: Username/owner of the fine-tuned model (e.g., "sundai-club")
        model_name: Name of the fine-tuned model
        trigger_word: Optional trigger word for the fine-tuned model.
                     If provided, will be prepended to the prompt.
        num_inference_steps: Number of inference steps
        guidance_scale: How much attention the model pays to the prompt
        model_type: Type of model to use ("dev" or "schnell")
        api_key: Optional Replicate API key. If None, uses config or environment variable.
        config: Optional config dictionary. If provided, will use api_key from config.
        download: If True, download the image to .images folder (default: True)
        output_dir: Optional directory to save image. If None, uses .images in project root.
        filename: Optional filename for saved image. If None, generates timestamp-based name.
    
    Returns:
        Dictionary with 'url' (image URL) and optionally 'file_path' (if download=True)
    """
    setup_replicate(api_key, config)
    
    # Get the latest version of the model
    model = replicate.models.get(owner=model_owner, name=model_name)
    latest_version = model.versions.list()[0]
    
    # Add trigger word if provided
    if trigger_word:
        full_prompt = f"{trigger_word} {prompt}"
    else:
        full_prompt = prompt
    
    input_params = {
        "prompt": full_prompt,
        "num_inference_steps": num_inference_steps,
        "guidance_scale": guidance_scale,
        "model": model_type,
    }
    
    output = replicate.run(latest_version, input=input_params)
    generated_img_url = str(output[0])
    
    result = {"url": generated_img_url}
    
    # Download image if requested
    if download:
        try:
            file_path = download_image(generated_img_url, output_dir, filename)
            result["file_path"] = str(file_path)
        except Exception as e:
            print(f"Warning: Failed to download image: {e}")
            print(f"Image URL: {generated_img_url}")
    
    return result


if __name__ == "__main__":
    # Load configuration
    try:
        config = load_config()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        exit(1)
    
    
    # Option 2: Generate with fine-tuned model
    print("\nGenerating image with fine-tuned model...")
    result = generate_image_finetuned(
        prompt="smiled at me in a space shuttle",
        model_owner=config.get("replicate_username", "sundai-club"),
        model_name=config.get("finetuned_model_name", "lty_model"),
        trigger_word=config.get("trigger_word", "lty"),
        num_inference_steps=28,
        guidance_scale=7.5,
        model_type="dev",
        config=config,
        download=True
    )
    print(f"Generated image URL: {result['url']}")
    if 'file_path' in result:
        print(f"Downloaded to: {result['file_path']}")
