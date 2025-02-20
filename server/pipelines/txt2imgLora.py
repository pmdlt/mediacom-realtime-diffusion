from diffusers import DiffusionPipeline, AutoencoderTiny, LCMScheduler
from compel import Compel
import torch

try:
    import intel_extension_for_pytorch as ipex  # type: ignore
except:
    pass

import psutil
from config import Args
from pydantic import BaseModel, Field
from PIL import Image

base_model = "wavymulder/Analog-Diffusion"
lcm_lora_id = "latent-consistency/lcm-lora-sdv1-5"
taesd_model = "madebyollin/taesd"

default_prompt = "Analog style photograph of young Harrison Ford as Han Solo, star wars behind the scenes"

page_content = """
<h1 class="text-3xl font-bold">Real-Time Latent Consistency Model SDv1.5</h1>
<h3 class="text-xl font-bold">Text-to-Image LCM + LoRa</h3>
<p class="text-sm">
    This demo showcases
    <a
    href="https://huggingface.co/blog/lcm_lora"
    target="_blank"
    class="text-blue-500 underline hover:no-underline">LCM</a>
Image to Image pipeline using
    <a
    href="https://huggingface.co/docs/diffusers/main/en/using-diffusers/lcm#performing-inference-with-lcm"
    target="_blank"
    class="text-blue-500 underline hover:no-underline">Diffusers</a
    > with a MJPEG stream server. Featuring <a
    href="https://huggingface.co/wavymulder/Analog-Diffusion"
    target="_blank"
    class="text-blue-500 underline hover:no-underline">Analog-Diffusion</a>
</p>
<p class="text-sm text-gray-500">
    Change the prompt to generate different images, accepts <a
    href="https://github.com/damian0815/compel/blob/main/doc/syntax.md"
    target="_blank"
    class="text-blue-500 underline hover:no-underline">Compel</a
    > syntax.
</p>
"""


class Pipeline:
    class Info(BaseModel):
        name: str = "controlnet"
        title: str = "Text-to-Image LCM + LoRa"
        description: str = "Generates an image from a text prompt"
        input_mode: str = "text"
        page_content: str = page_content

    class InputParams(BaseModel):
        prompt: str = Field(
            default_prompt,
            title="Prompt",
            field="textarea",
            id="prompt",
        )
        seed: int = Field(
            8638236174640251, min=0, title="Seed", field="seed", hide=True, id="seed"
        )
        steps: int = Field(
            4, min=2, max=15, title="Steps", field="range", hide=True, id="steps"
        )
        width: int = Field(
            512, min=2, max=15, title="Width", disabled=True, hide=True, id="width"
        )
        height: int = Field(
            512, min=2, max=15, title="Height", disabled=True, hide=True, id="height"
        )
        guidance_scale: float = Field(
            0.2,
            min=0,
            max=4,
            step=0.001,
            title="Guidance Scale",
            field="range",
            hide=True,
            id="guidance_scale",
        )

    def __init__(self, args: Args, device: torch.device, torch_dtype: torch.dtype):
        self.pipe = DiffusionPipeline.from_pretrained(base_model, safety_checker=None)
        if args.taesd:
            self.pipe.vae = AutoencoderTiny.from_pretrained(
                taesd_model, torch_dtype=torch_dtype, use_safetensors=True
            ).to(device)

        self.pipe.scheduler = LCMScheduler.from_config(self.pipe.scheduler.config)
        self.pipe.set_progress_bar_config(disable=True)
        self.pipe.load_lora_weights(lcm_lora_id, adapter_name="lcm")
        self.pipe.to(device=device, dtype=torch_dtype)

        if device.type != "mps":
            self.pipe.unet.to(memory_format=torch.channels_last)

        if args.torch_compile:
            self.pipe.unet = torch.compile(
                self.pipe.unet, mode="reduce-overhead", fullgraph=True
            )
            self.pipe.vae = torch.compile(
                self.pipe.vae, mode="reduce-overhead", fullgraph=True
            )

            self.pipe(prompt="warmup", num_inference_steps=1, guidance_scale=8.0)

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

        if args.compel:
            self.compel_proc = Compel(
                tokenizer=self.pipe.tokenizer,
                text_encoder=self.pipe.text_encoder,
                truncate_long_prompts=False,
            )

    def predict(self, params: "Pipeline.InputParams") -> Image.Image:
        generator = torch.manual_seed(params.seed)
        prompt_embeds = None
        prompt = params.prompt
        if hasattr(self, "compel_proc"):
            prompt_embeds = self.compel_proc(params.prompt)
            prompt = None

        results = self.pipe(
            prompt=prompt,
            prompt_embeds=prompt_embeds,
            generator=generator,
            num_inference_steps=params.steps,
            guidance_scale=params.guidance_scale,
            width=params.width,
            height=params.height,
            output_type="pil",
        )

        return results.images[0]
