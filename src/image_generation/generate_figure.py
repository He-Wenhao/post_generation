# -*- coding: utf-8 -*-
"""
Image generation script using Replicate's Flux model.
Generates images from text prompts without training functionality.
"""

import os
import replicate
from typing import Optional, List


def setup_replicate(api_key: Optional[str] = None):
    """
    Setup Replicate API key.
    
    Args:
        api_key: Replicate API key. If None, will use REPLICATE_API_TOKEN env var.
    """
    if api_key:
        os.environ["REPLICATE_API_TOKEN"] = api_key
    elif not os.environ.get("REPLICATE_API_TOKEN"):
        raise ValueError(
            "Replicate API key not found. Please set REPLICATE_API_TOKEN environment variable "
            "or pass api_key parameter."
        )


def generate_image(
    prompt: str,
    model: str = "black-forest-labs/flux-dev",
    num_inference_steps: int = 28,
    guidance_scale: float = 7.5,
    model_type: str = "dev",
    api_key: Optional[str] = None
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
        api_key: Optional Replicate API key. If None, uses environment variable.
    
    Returns:
        URL of the generated image
    
    Example:
        >>> url = generate_image("A photo of a dog in a space shuttle")
        >>> print(url)
    """
    setup_replicate(api_key)
    
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
    api_key: Optional[str] = None
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
        api_key: Optional Replicate API key
    
    Returns:
        URL of the generated image
    """
    setup_replicate(api_key)
    
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
    # Example usage
    REPLICATE_API_KEY = #"YOUR_API_KEY_HERE"
    # Option 1: Generate with base model
    print("Generating image with base Flux model...")
    '''
    image_url = generate_image(
        prompt="A photo of a dog in a space shuttle",
        num_inference_steps=28,
        guidance_scale=7.5,
        model_type="dev",
        api_key=REPLICATE_API_KEY
    )
    print(f"Generated image URL: {image_url}")
    '''
    # Option 2: Generate with fine-tuned model (uncomment and fill in details)
    # print("\nGenerating image with fine-tuned model...")
    image_url = generate_image_finetuned(
        prompt="smiled at me in a space shuttle",
        model_owner="sundai-club",
        model_name="lty_model",
        trigger_word="lty",
        num_inference_steps=28,
        guidance_scale=7.5,
        model_type="dev",
        api_key=REPLICATE_API_KEY
    )
    print(f"Generated image URL: {image_url}")
