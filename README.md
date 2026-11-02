
some notes
1. config.py
using dataclass to store the default setting.
A dataclass in Python is a class primarily designed to store data and state

• Default Values: You can assign standard defaults (e.g., age: int = 18) or use field(default_factory=...) for mutable types like lists or dicts.

• Immutability: Passing frozen=True to the decorator makes the instance read-only (immutable), raising an error if you try to change an attribute.

• Comparison: Passing order=True automatically creates sorting and comparison methods based on the order fields are declared