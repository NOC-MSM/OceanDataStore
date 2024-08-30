"""Exception classes."""
import logging


class VariableNotFound(Exception):
    """Exception raised for when a variable is not found in the dataset."""

    def __init__(self, variable_name):
        """Initialise the exception."""
        message = f"Variable '{variable_name}' not found in the dataset."
        logging.warning(message)
        super().__init__(message)

class DuplicatedAppendDimValue(Exception):
    """Exception raised for when a duplicated value is found in the append dim."""

    def __init__(self, n_dupl, append_dim, first_dupl_value, last_dupl_value):
        """Initialise the exception."""
        msg_general = (
            f"Found {n_dupl} duplicates in the append dimension '{append_dim}'."
        )
        msg_specific = f"Range: {first_dupl_value}--{last_dupl_value}."
        logging.warning(msg_general)
        logging.warning(msg_specific)
        message = msg_general + msg_specific
        super().__init__(message)

class DimensionMismatch(Exception):
    """Exception raised for when a dimension mismatch is found"""

    def __init__(self, dim, size, expected_size):
        """Initialise the exception."""
        message = f"Dimension {dim} has size {size}, expected {expected_size}."
        logging.warning(message)
        super().__init__(message)

class ExpectedAttrsNotFound(Exception):
    """Exception raised for when expected attributes are not found in the metadata."""

    def __init__(self, expected_attrs):
        """Initialise the exception."""
        message = f"Expected {expected_attrs} not found in metadata."
        logging.warning(message)
        super().__init__(message)

class CheckSumMismatch(Exception):
    """Exception raised for when a checksum mismatch is found."""

    def __init__(self, append_dim, expected_checksum, actual_checksum):
        """Initialise the exception."""
        message = (
            f"Checksum mismatch for append dim {append_dim}. Expected: {expected_checksum}, Actual: {actual_checksum}"
        )
        logging.warning(message)
        super().__init__(message)
