---
license: apache-2.0
base_model: Qwen/Qwen3.5-4B
tags:
  - peft
  - lora
  - qwen
  - qwen3.5
  - nassila
  - sanad
  - l3-grounding
  - ouroboros
  - academic
language:
  - en
  - ar
library_name: peft
---

# Nassila Sanad 4B LoRA Adapter

**Checkpoint:** **S15** *(train label v1.15)*

LoRA adapter weights for **Sanad** in [Nassila](https://github.com/jamalesam93/Nassila) — fine-tuned on `Qwen/Qwen3.5-4B` for academic manuscript claim grounding and citation verification.

* **Base Model:** [`Qwen/Qwen3.5-4B`](https://huggingface.co/Qwen/Qwen3.5-4B)
* **GGUF Model Repo:** [`QinEmPeRoR93/nassila-sanad-4b`](https://huggingface.co/QinEmPeRoR93/nassila-sanad-4b)
* **LoRA Parameters:** Rank $r=16$, Alpha $\alpha=32$, Dropout $0.05$
* **Target Modules:** `["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]`

## Usage with PEFT / Transformers

```python
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

base_model = "Qwen/Qwen3.5-4B"
adapter_model = "QinEmPeRoR93/nassila-sanad-4b-lora"

tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    base_model,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True,
)
model = PeftModel.from_pretrained(model, adapter_model)
```

## Performance

Fine-tuned on the Nassila 874-row L3 grounding dataset. On the 308-row contrastive holdout benchmark:
* **False-Supported Rate:** **4.87%** (Passes $\le 5\%$ safety gate)
* **Contradiction Pass Rate:** **85.83%**
* **`not_in_source` Pass Rate:** **100.0%**
