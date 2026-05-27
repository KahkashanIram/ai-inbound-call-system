from app.services.audio_converter import AudioConverter


def test_conversion():
    # 🔹 Load original PCM audio (from TTS)
    with open("output_0.raw", "rb") as f:
        pcm_audio = f.read()

    print(f"📦 Original PCM size: {len(pcm_audio)}")

    # 🔹 Convert PCM → μ-law
    mulaw_audio = AudioConverter.pcm_to_mulaw(pcm_audio)
    print(f"📦 μ-law size: {len(mulaw_audio)}")

    # 🔹 Convert back μ-law → PCM
    pcm_back = AudioConverter.mulaw_to_pcm(mulaw_audio)
    print(f"📦 Reconstructed PCM size: {len(pcm_back)}")

    # 🔹 Save all files for listening
    with open("output_mulaw.raw", "wb") as f:
        f.write(mulaw_audio)

    with open("output_pcm_back.raw", "wb") as f:
        f.write(pcm_back)

    print("✅ Files saved:")
    print("   - output_mulaw.raw")
    print("   - output_pcm_back.raw")


if __name__ == "__main__":
    test_conversion()