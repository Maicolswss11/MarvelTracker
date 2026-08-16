#!/usr/bin/env python3
"""Doctor Strange audited builder corrections layered over the base builder.

Doctor Strange (1974) #21 is a straight reprint of Doctor Strange (1968) #169,
not a new chapter in the 1974 narrative spine.  It must therefore not create a
second reading step between #20 and #22.
"""
from __future__ import annotations

import build_doctor_strange_audit as base


for spec in base.SOURCE_SPECS:
    if spec.get("code") == "DS2":
        spec["include"] = lambda n: 1 <= n <= 81 and n != 21
        break
else:
    raise RuntimeError("Doctor Strange DS2 source specification not found")


if __name__ == "__main__":
    base.main()
