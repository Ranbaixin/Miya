import argparse
import os
import sys
import time

base = (
    r"D:\AIvoice\GPT-SoVITS-v2pro-20250604-nvidia50\GPT-SoVITS-v2pro-20250604-nvidia50"
)
sys.path.insert(0, base)
sys.path.insert(0, os.path.join(base, "tools", "uvr5"))
os.chdir(base)

import torch


def _rename_vr_output(input_audio, output_vocal, output_inst):
    vocal_dir = os.path.dirname(output_vocal)
    inst_dir = os.path.dirname(output_inst)

    for root in [vocal_dir, inst_dir]:
        for f in os.listdir(root):
            fp = os.path.join(root, f)
            if not f.endswith(".wav") or f in ("Vocals.wav", "Instrumental.wav"):
                continue
            fl = f.lower()
            sz = os.path.getsize(fp)
            if sz < 1024:
                continue
            if "vocal" in fl and "instrument" not in fl:
                if os.path.exists(output_vocal):
                    os.remove(output_vocal)
                os.rename(fp, output_vocal)
            elif "instrument" in fl or "no_vocal" in fl or "other" in fl:
                if os.path.exists(output_inst):
                    os.remove(output_inst)
                os.rename(fp, output_inst)


def run_vr(input_audio, output_vocal, output_inst, model_path, device="cuda", agg=10):
    from tools.uvr5.vr import AudioPre

    ap = AudioPre(agg=agg, model_path=model_path, device=device, is_half=True)
    ap._path_audio_(
        input_audio,
        ins_root=os.path.dirname(output_inst),
        vocal_root=os.path.dirname(output_vocal),
        format="wav",
    )
    _rename_vr_output(input_audio, output_vocal, output_inst)
    return os.path.exists(output_vocal), os.path.exists(output_inst)


def run_bs_roformer(input_audio, output_vocal, output_inst, model_path, device="cuda"):
    from tools.uvr5.bsroformer import Roformer_Loader

    rl = Roformer_Loader(
        model_path=model_path, config_path="", device=device, is_half=True
    )
    rl._path_audio_(
        input_audio,
        others_root=os.path.dirname(output_inst),
        vocal_root=os.path.dirname(output_vocal),
        format="wav",
    )
    _rename_vr_output(input_audio, output_vocal, output_inst)
    return os.path.exists(output_vocal), os.path.exists(output_inst)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UVR5 Vocal Separation CLI")
    parser.add_argument("input", help="Input audio file")
    parser.add_argument("output_dir", help="Output directory")
    parser.add_argument("--model-type", default="vr", choices=["vr", "bs_roformer"])
    parser.add_argument(
        "--model-path", required=True, help="Path to .pth or .ckpt model"
    )
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--agg", type=int, default=10)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    vocal_out = os.path.join(args.output_dir, "Vocals.wav")
    inst_out = os.path.join(args.output_dir, "Instrumental.wav")

    t0 = time.time()
    if args.model_type == "vr":
        v_ok, i_ok = run_vr(
            args.input, vocal_out, inst_out, args.model_path, args.device, args.agg
        )
    else:
        v_ok, i_ok = run_bs_roformer(
            args.input, vocal_out, inst_out, args.model_path, args.device
        )
    elapsed = time.time() - t0

    if v_ok:
        print(
            f"OK {elapsed:.1f}s vocal={os.path.getsize(vocal_out)}B inst={os.path.getsize(inst_out) if i_ok else 0}B"
        )
    else:
        print(f"FAIL {elapsed:.1f}s", file=sys.stderr)
        sys.exit(1)
