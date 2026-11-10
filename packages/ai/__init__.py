"""Model boundaries: transcription, language model, clause search, citation validation.

Every external model sits behind a Protocol with a deterministic fake. No real
provider is called in B1 (AD-4, AD-5 open). The model never decides a vote,
quorum, access or retention outcome.
"""
