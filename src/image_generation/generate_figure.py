# -*- coding: utf-8 -*-
"""
Image generation script using Replicate's Flux model.
Generates images from text prompts without training functionality.
"""

import os
import json
from pathlib import Path
import replicate
from typing import Optional, Dict


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
        project_root = Path(__file__).parent.parent.parent
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
    config: Optional[Dict] = None
) -> str:
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
    
    Returns:
        URL of the generated image
    
    Example:
        >>> url = generate_image("A photo of a dog in a space shuttle")
        >>> print(url)
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
    
    return generated_img_url


def generate_image_finetuned(
    prompt: str,
    model_owner: str,
    model_name: str,
    trigger_word: Optional[str] = None,
    num_inference_steps: int = 28,
    guidance_scale: float = 7.5,
    model_type: str = "dev",
    api_key: Optional[str] = None,
    config: Optional[Dict] = None
) -> str:
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
    
    Returns:
        URL of the generated image
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
    
    return generated_img_url


if __name__ == "__main__":
    # Load configuration
    try:
        config = load_config()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        exit(1)
    
    # Option 1: Generate with base model
    print("Generating image with base Flux model...")
    '''
    image_url = generate_image(
        prompt="A photo of a dog in a space shuttle",
        num_inference_steps=28,
        guidance_scale=7.5,
        model_type="dev",
        config=config
    )
    print(f"Generated image URL: {image_url}")
    '''
    
    # Option 2: Generate with fine-tuned model
    print("\nGenerating image with fine-tuned model...")
    image_url = generate_image_finetuned(
        prompt="smiled at me in a space shuttle",
        model_owner=config.get("replicate_username", "sundai-club"),
        model_name=config.get("finetuned_model_name", "lty_model"),
        trigger_word=config.get("trigger_word", "lty"),
        num_inference_steps=28,
        guidance_scale=7.5,
        model_type="dev",
        config=config
    )
    print(f"Generated image URL: {image_url}")
