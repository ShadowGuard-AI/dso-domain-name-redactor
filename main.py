import argparse
import logging
import re
import sys
from faker import Faker
import chardet

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.
    """
    parser = argparse.ArgumentParser(
        description="Redacts domain names from text while preserving the TLD."
    )
    parser.add_argument(
        "input_file",
        help="Path to the input text file."
    )
    parser.add_argument(
        "output_file",
        help="Path to the output text file."
    )
    parser.add_argument(
        "-l",
        "--language",
        default="en_US",
        help="Language locale for Faker (default: en_US)."
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug logging."
    )
    return parser.parse_args()


def redact_domain_name(text, language="en_US"):
    """
    Redacts domain names from the input text, preserving the TLD.

    Args:
        text (str): The input text to redact.
        language (str): The language locale for Faker.

    Returns:
        str: The redacted text.
    """
    fake = Faker(language)
    domain_pattern = r"([a-zA-Z0-9.-]+)\.([a-zA-Z]{2,})"  # Matches domain names. TLD must be at least 2 chars
    
    def replace_domain(match):
        """Replaces the domain part while keeping the TLD."""
        tld = match.group(2)
        new_domain = fake.domain_word()
        return f"{new_domain}.{tld}"
    
    redacted_text = re.sub(domain_pattern, replace_domain, text)
    return redacted_text


def detect_encoding(file_path):
    """Detects the encoding of a file.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The detected encoding.
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            return result['encoding']
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        raise
    except Exception as e:
        logging.error(f"Error detecting encoding for {file_path}: {e}")
        return None

def read_file_content(input_file):
    """Reads the content of a file, handling encoding detection.

    Args:
        input_file (str): Path to the input file.

    Returns:
        str: The content of the file, or None on error.
    """
    try:
        encoding = detect_encoding(input_file)
        if not encoding:
            logging.warning(f"Could not detect encoding for {input_file}.  Trying UTF-8.")
            encoding = 'utf-8' # Default fallback
        with open(input_file, 'r', encoding=encoding, errors='replace') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        logging.error(f"Input file not found: {input_file}")
        return None
    except Exception as e:
        logging.error(f"Error reading file {input_file}: {e}")
        return None


def write_file_content(output_file, content):
    """Writes content to a file.

    Args:
        output_file (str): Path to the output file.
        content (str): The content to write.
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        logging.error(f"Error writing to file {output_file}: {e}")
        sys.exit(1)

def main():
    """
    Main function to execute the domain name redaction.
    """
    args = setup_argparse()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Debug mode enabled.")

    input_file = args.input_file
    output_file = args.output_file
    language = args.language

    logging.info(f"Reading input file: {input_file}")
    text = read_file_content(input_file)

    if text is None:
        logging.error("Failed to read input file. Exiting.")
        sys.exit(1)

    logging.info("Redacting domain names...")
    try:
        redacted_text = redact_domain_name(text, language)
    except Exception as e:
        logging.error(f"Error during redaction: {e}")
        sys.exit(1)

    logging.info(f"Writing redacted text to: {output_file}")
    write_file_content(output_file, redacted_text)

    logging.info("Domain name redaction complete.")


if __name__ == "__main__":
    main()