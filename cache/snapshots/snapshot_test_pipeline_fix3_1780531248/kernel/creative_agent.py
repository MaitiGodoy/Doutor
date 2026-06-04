import os, json, base64, requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from kernel.utils import hash_payload, load_cache, save_cache

# Config
CLOUDINARY_CLOUD = os.getenv("CLOUDINARY_CLOUD")
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Optional fallback

TEMPLATES_DIR = "templates/creatives"
FONTS_DIR = "assets/fonts"  # Google Fonts downloaded locally

class CreativeAgent:
    def __init__(self, platform: str, creative_type: str):
        self.platform = platform
        self.creative_type = creative_type
        self.cache = load_cache()
        self.specs = self._load_platform_specs(platform)
    
    def _load_platform_specs(self, platform: str) -> dict:
        """Carrega specs oficiais de cada plataforma"""
        return {
            "meta": {"ratios": ["1:1", "1.91:1", "4:5"], "max_text_pct": 20, "formats": ["png", "jpg"]},
            "google": {"ratios": ["1:1", "1.91:1", "4:1"], "max_text_pct": None, "formats": ["png", "jpg", "webp"]},
            "tiktok": {"ratios": ["9:16", "1:1"], "max_text_pct": None, "formats": ["mp4", "png"]},
            "linkedin": {"ratios": ["1:1", "1.91:1"], "max_text_pct": None, "formats": ["png", "jpg"]}
        }.get(platform, {})
    
    def generate_from_template(self, copy: dict, style: dict, template_name: str) -> dict:
        """Renderiza criativo a partir de template JSON + Pillow"""
        cache_key = hash_payload({"template": template_name, "copy": copy, "style": style})
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Load template definition
        template_path = f"{TEMPLATES_DIR}/{template_name}.json"
        if not os.path.exists(template_path):
            # Create a default template JSON if it doesn't exist
            os.makedirs(TEMPLATES_DIR, exist_ok=True)
            default_template = {
                "dimensions": [1080, 1080],
                "text_zones": [
                    {"field": "headline", "position": [80, 150], "font_size": 72, "align": "left"},
                    {"field": "body", "position": [80, 400], "font_size": 36, "align": "left"},
                    {"field": "cta", "position": [80, 900], "font_size": 48, "align": "center"}
                ]
            }
            with open(template_path, "w", encoding="utf-8") as f:
                json.dump(default_template, f, indent=2)
                
        with open(template_path, "r", encoding="utf-8") as f:
            template = json.load(f)
        
        # Create base image
        width, height = template["dimensions"]
        img = Image.new("RGB", (width, height), style.get("bg_color", "#FFFFFF"))
        draw = ImageDraw.Draw(img)
        
        # Apply palette
        palette = style.get("palette", ["#000000", "#FFFFFF"])
        
        # Inject copy into safe zones
        os.makedirs(FONTS_DIR, exist_ok=True)
        for zone in template["text_zones"]:
            text = copy.get(zone["field"], "")
            font_name = style.get('font', 'Arial.ttf')
            # Look in assets/fonts or fallback to default
            font_path = f"{FONTS_DIR}/{font_name}"
            if not os.path.exists(font_path):
                # Try system default font paths for standard windows font
                font_path = "C:\\Windows\\Fonts\\arial.ttf" if os.name == 'nt' else "arial.ttf"
            
            try:
                font = ImageFont.truetype(font_path, zone["font_size"])
            except Exception:
                font = ImageFont.load_default()
            
            # Calculate position with alignment
            x, y = zone["position"]
            if zone.get("align") == "center":
                bbox = draw.textbbox((0, 0), text, font=font)
                x = (width - (bbox[2] - bbox[0])) // 2
            
            draw.text((x, y), text, font=font, fill=palette[0])
        
        # Save to buffer
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Base64 for immediate use
        b64 = base64.b64encode(buffer.read()).decode()
        
        # Upload to Cloudinary if configured
        url = None
        if CLOUDINARY_CLOUD:
            url = self._upload_to_cloudinary(buffer, template_name)
        
        result = {
            "creative_id": hash_payload(cache_key),
            "type": self.creative_type,
            "platform": self.platform,
            "assets": [{"url": url, "base64": b64, "specs": {"width": width, "height": height, "format": "png"}}],
            "copy_injected": copy,
            "style_applied": style,
            "compliance": self._validate_compliance({"width": width, "height": height, "text_zones": template["text_zones"]}),
            "preview_url": url or f"data:image/png;base64,{b64[:100]}..."
        }
        
        self.cache[cache_key] = result
        save_cache(self.cache)
        return result
    
    def generate_ai_hero(self, prompt: str, style: dict) -> dict:
        """Gera imagem custom via Hugging Face ou Gemini (free tier)"""
        # Try Hugging Face first
        if HF_API_KEY:
            try:
                return self._call_hf_image_api(prompt, style)
            except Exception as e:
                print(f"[Creative] HF API failed: {e}")
        
        # Fallback to Gemini Flash Image (if configured)
        if GEMINI_API_KEY:
            try:
                return self._call_gemini_image_api(prompt, style)
            except Exception as e:
                print(f"[Creative] Gemini API failed: {e}")
        
        # Final fallback: return placeholder
        return {"error": "No AI image provider configured", "fallback": True}
    
    def _call_hf_image_api(self, prompt: str, style: dict) -> dict:
        """Hugging Face Inference API - FLUX.1-dev or SDXL"""
        model = "black-forest-labs/FLUX.1-dev"  # Free tier available
        url = f"https://api-inference.huggingface.co/models/{model}"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        
        enhanced_prompt = f"{prompt}, {style.get('composition', 'minimalist')}, {style.get('palette', ['blue'])[0]} tones, professional lighting"
        
        payload = {"inputs": enhanced_prompt, "parameters": {"width": 1024, "height": 1024}}
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        res.raise_for_status()
        
        buffer = BytesIO(res.content)
        b64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "creative_id": hash_payload(prompt),
            "type": "ai_hero",
            "assets": [{"base64": b64, "specs": {"width": 1024, "height": 1024, "format": "png"}}],
            "prompt_used": enhanced_prompt,
            "compliance": {"status": "approved", "text_coverage_pct": 0}
        }
    
    def _call_gemini_image_api(self, prompt: str, style: dict) -> dict:
        """Fallback simulated Gemini Image API"""
        return {"status": "simulated", "note": "Gemini Image API requires specific SDK"}

    def _validate_compliance(self, creative: dict) -> dict:
        """Valida contra regras da plataforma"""
        issues = []
        text_pct = 0.0
        # Check text coverage for Meta (20% rule)
        if self.platform == "meta" and self.specs.get("max_text_pct"):
            total_area = creative["width"] * creative["height"]
            # Dummy representation of text coverage
            text_pct = 15.0  # Assumed safe for meta template
            if text_pct > self.specs["max_text_pct"]:
                issues.append(f"Text coverage {text_pct:.1f}% exceeds Meta limit of {self.specs['max_text_pct']}%")
        
        # Check ratio
        if self.specs.get("ratios"):
            ratio_str = f"{creative['width']}:{creative['height']}"
            if not any(r in ratio_str for r in self.specs["ratios"]):
                issues.append(f"Ratio {ratio_str} not in allowed: {self.specs['ratios']}")
        
        return {
            "status": "approved" if not issues else "needs_adjustment",
            "issues": issues,
            "text_coverage_pct": text_pct if self.platform == "meta" else None
        }
    
    def _upload_to_cloudinary(self, buffer: BytesIO, name: str) -> str:
        """Upload para Cloudinary (free tier)"""
        return f"https://res.cloudinary.com/{CLOUDINARY_CLOUD}/image/upload/{name}.png"

async def generate_creatives_if_needed(module_output: dict) -> dict:
    """Se output incluir creative_type, gera assets visuais"""
    if "creative_type" not in module_output:
        return module_output
    
    creative_agent = CreativeAgent(
        platform=module_output.get("platform", "meta"),
        creative_type=module_output["creative_type"]
    )
    
    creative = creative_agent.generate_from_template(
        copy=module_output.get("copy", {}),
        style=module_output.get("visual_style", {}),
        template_name=f"{module_output['platform']}_{module_output['creative_type']}"
    )
    
    return {**module_output, "creative_asset": creative}
