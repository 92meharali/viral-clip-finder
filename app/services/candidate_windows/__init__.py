"""Candidate window generation package."""

from app.services.candidate_windows.generator import (
    CandidateWindowGenerator,
    generate_candidate_windows,
)

__all__ = [
    "CandidateWindowGenerator",
    "generate_candidate_windows",
]
