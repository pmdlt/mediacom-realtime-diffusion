from diffusers import (
    AutoPipelineForImage2Image,
    AutoencoderTiny,
)
from compel import Compel, ReturnedEmbeddingsType
import torch

try:
    import intel_extension_for_pytorch as ipex  # type: ignore
except:
    pass

import psutil
from config import Args
from pydantic import BaseModel, Field
from PIL import Image
import math

base_model = "stabilityai/sdxl-turbo"
taesd_model = "madebyollin/taesdxl"

default_prompt = "A young girl with rosy cheeks and bright eyes, dressed in traditional Swiss alpine clothing, stands joyfully on a lush green mountain meadow. She has long, flowing brown hair tied in two braids, and she wears a simple yet charming dress with an apron. Around her, the majestic Swiss Alps rise with snow-capped peaks under a clear blue sky."
default_negative_prompt = "blurry, low quality, render, 3D, oversaturated"
page_content = """
<h1 class="text-3xl font-bold">Testez la démo que nous préparons pour Osaka 2025 !</h1>
<h3 class="text-xl font-bold">Changez le prompt et voyez les changements s'effectuer en direct.</h3>
<p class="text-sm">
 Celui ou celle qui trouvera le meilleur prompt (qu'on utilisera pour Osaka) se verra offrir une bière à Sat' par Paul ! 🍻
</p>
"""


class Pipeline:
    class Info(BaseModel):
        name: str = "img2img"
        title: str = "Image-to-Image SDXL"
        description: str = "Generates an image from a text prompt"
        input_mode: str = "image"
        page_content: str = page_content

    class InputParams(BaseModel):
        prompt: str = Field(
            default_prompt,
            title="Prompt",
            field="textarea",
            id="prompt",
        )
        negative_prompt: str = Field(
            default_negative_prompt,
            title="Negative Prompt",
            field="textarea",
            id="negative_prompt",
            hide=True,
        )
        seed: int = Field(
            2159232, min=0, title="Seed", field="seed", hide=True, id="seed"
        )
        steps: int = Field(
            1, min=1, max=10, title="Steps", field="range", hide=True, id="steps"
        )
        width: int = Field(
            512, min=2, max=15, title="Width", disabled=True, hide=True, id="width"
        )
        height: int = Field(
            512, min=2, max=15, title="Height", disabled=True, hide=True, id="height"
        )
        guidance_scale: float = Field(
            1.0,
            min=0,
            max=1,
            step=0.001,
            title="Guidance Scale",
            field="range",
            hide=True,
            id="guidance_scale",
        )
        strength: float = Field(
            0.5,
            min=0.25,
            max=1.0,
            step=0.001,
            title="Strength",
            field="range",
            hide=True,
            id="strength",
        )

    def __init__(self, args: Args, device: torch.device, torch_dtype: torch.dtype):
        self.pipe = AutoPipelineForImage2Image.from_pretrained(
            base_model,
            safety_checker=None,
        )
        if args.taesd:
            self.pipe.vae = AutoencoderTiny.from_pretrained(
                taesd_model, torch_dtype=torch_dtype, use_safetensors=True
            ).to(device)

        if args.sfast:
            from sfast.compilers.stable_diffusion_pipeline_compiler import (
                compile,
                CompilationConfig,
            )

            config = CompilationConfig.Default()
            config.enable_xformers = True
            config.enable_triton = True
            config.enable_cuda_graph = True
            self.pipe = compile(self.pipe, config=config)

        self.pipe.set_progress_bar_config(disable=True)
        self.pipe.to(device=device, dtype=torch_dtype)
        if device.type != "mps":
            self.pipe.unet.to(memory_format=torch.channels_last)

        if args.torch_compile:
            print("Running torch compile")
            self.pipe.unet = torch.compile(
                self.pipe.unet, mode="reduce-overhead", fullgraph=True
            )
            self.pipe.vae = torch.compile(
                self.pipe.vae, mode="reduce-overhead", fullgraph=True
            )
            self.pipe(
                prompt="warmup",
                image=[Image.new("RGB", (768, 768))],
            )

        if args.compel:
            self.pipe.compel_proc = Compel(
                tokenizer=[self.pipe.tokenizer, self.pipe.tokenizer_2],
                text_encoder=[self.pipe.text_encoder, self.pipe.text_encoder_2],
                returned_embeddings_type=ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED,
                requires_pooled=[False, True],
            )

    def predict(self, params: "Pipeline.InputParams") -> Image.Image:
        generator = torch.manual_seed(params.seed)
        prompt = params.prompt
        negative_prompt = params.negative_prompt
        prompt_embeds = None
        pooled_prompt_embeds = None
        negative_prompt_embeds = None
        negative_pooled_prompt_embeds = None
        if hasattr(self.pipe, "compel_proc"):
            _prompt_embeds, pooled_prompt_embeds = self.pipe.compel_proc(
                [params.prompt, params.negative_prompt]
            )
            prompt = None
            negative_prompt = None
            prompt_embeds = _prompt_embeds[0:1]
            pooled_prompt_embeds = pooled_prompt_embeds[0:1]
            negative_prompt_embeds = _prompt_embeds[1:2]
            negative_pooled_prompt_embeds = pooled_prompt_embeds[1:2]

        steps = params.steps
        strength = params.strength
        if int(steps * strength) < 1:
            steps = math.ceil(1 / max(0.10, strength))

        results = self.pipe(
            image=params.image,
            prompt=prompt,
            negative_prompt=negative_prompt,
            prompt_embeds=prompt_embeds,
            pooled_prompt_embeds=pooled_prompt_embeds,
            negative_prompt_embeds=negative_prompt_embeds,
            negative_pooled_prompt_embeds=negative_pooled_prompt_embeds,
            generator=generator,
            strength=strength,
            num_inference_steps=steps,
            guidance_scale=params.guidance_scale,
            width=params.width,
            height=params.height,
            output_type="pil",
        )

        return results.images[0]
