"""multilingual-e5-small (quantized ONNX) — encoder χωρίς PyTorch."""
import numpy as np, onnxruntime as ort
from tokenizers import Tokenizer
class E5:
    def __init__(self, model_dir):
        self.tok = Tokenizer.from_file(f"{model_dir}/tokenizer.json")
        self.tok.enable_truncation(512); self.tok.enable_padding()
        so = ort.SessionOptions(); so.intra_op_num_threads = 4
        self.sess = ort.InferenceSession(f"{model_dir}/model_quantized.onnx", so, providers=["CPUExecutionProvider"])
        self.inputs = [i.name for i in self.sess.get_inputs()]
    def encode(self, texts, prefix, batch=32):
        out = []
        for i in range(0, len(texts), batch):
            enc = self.tok.encode_batch([prefix + t for t in texts[i:i+batch]])
            ids = np.array([e.ids for e in enc], dtype=np.int64)
            mask = np.array([e.attention_mask for e in enc], dtype=np.int64)
            feed = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self.inputs: feed["token_type_ids"] = np.zeros_like(ids)
            h = self.sess.run(None, feed)[0]
            m = mask[..., None].astype(np.float32)
            v = (h * m).sum(1) / m.sum(1)
            out.append(v / np.linalg.norm(v, axis=1, keepdims=True))
        return np.vstack(out).astype(np.float32)
