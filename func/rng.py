"""
Independent random number streams.

Every generation step draws from its own NumPy Generator seeded with (random_state, stream number). A change in one
step (for example the dirty-data level) then never shifts the random numbers of another step, and the same seed
still gives the same data. Names, phone numbers and bank accounts come from Faker, seeded separately.
"""
import numpy as np

import settings.main_settings as s

STREAMS = {
    "calendar": 1,
    "customers": 2,
    "behaviour": 3,
    "orders": 4,
    "anomalies": 5,
    "quality": 6,
    "prices": 7,
    "returns": 8,
    "logistics": 9,
    "basket": 10,
    "marketing": 11,
    "sessions": 12,
    "experiments": 13,
    "products": 14,
    "order_status": 15,
    "reviews": 16,
    "competitors": 17,
}


def stream(name: str) -> np.random.Generator:
    """
    Return a NumPy Generator for one named step.

    Parameters:
    name (str): Stream name from STREAMS.

    Returns:
    np.random.Generator: Seeded with (random_state, stream number), or fresh entropy when random_state is None.
    """
    if name not in STREAMS:
        raise ValueError(f"Unknown random stream: {name}. Use one of {sorted(STREAMS)}.")
    if s.random_state is None:
        return np.random.default_rng()
    return np.random.default_rng([s.random_state, STREAMS[name]])
