import audioop


class AudioConverter:

    @staticmethod
    def mulaw_to_pcm(mulaw_bytes: bytes) -> bytes:
        """
        μ-law → PCM (16-bit)
        """
        return audioop.ulaw2lin(mulaw_bytes, 2)

    @staticmethod
    def pcm_to_mulaw(pcm_bytes: bytes, input_rate: int = 8000) -> bytes:
        """
        PCM → μ-law (Twilio compatible)
        """

        # 🔥 RESAMPLE if needed
        if input_rate != 8000:
            pcm_bytes, _ = audioop.ratecv(
                pcm_bytes,
                2,
                1,
                input_rate,
                8000,
                None
            )

        # 🔥 NORMALIZE volume
        pcm_bytes = audioop.mul(pcm_bytes, 2, 2.0)

        # 🔥 CONVERT
        return audioop.lin2ulaw(pcm_bytes, 2)