"""File I/O utility functions."""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List


def ensure_directory(path: Path) -> Path:
    """
    Ensure a directory exists, create if it doesn't.

    Args:
        path: Directory path

    Returns:
        Path object
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_timestamped_filename(base_name: str, extension: str = "json") -> str:
    """
    Generate a timestamped filename.

    Args:
        base_name: Base filename without extension
        extension: File extension (without dot)

    Returns:
        Timestamped filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}.{extension}"


def save_json(data: Any, filepath: Path, pretty: bool = True) -> None:
    """
    Save data to JSON file.

    Args:
        data: Data to save
        filepath: Output file path
        pretty: Whether to pretty-print JSON
    """
    filepath = Path(filepath)
    ensure_directory(filepath.parent)

    with open(filepath, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(data, f, ensure_ascii=False)


def load_json(filepath: Path) -> Any:
    """
    Load data from JSON file.

    Args:
        filepath: Input file path

    Returns:
        Loaded data
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_csv(data: List[Dict], filepath: Path, fieldnames: List[str] = None) -> None:
    """
    Save list of dicts to CSV file.

    Args:
        data: List of dictionaries
        filepath: Output file path
        fieldnames: Optional list of field names (if None, uses keys from first row)
    """
    if not data:
        return

    filepath = Path(filepath)
    ensure_directory(filepath.parent)

    if fieldnames is None:
        fieldnames = list(data[0].keys())

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def load_csv(filepath: Path) -> List[Dict]:
    """
    Load CSV file as list of dicts.

    Args:
        filepath: Input file path

    Returns:
        List of dictionaries
    """
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)
