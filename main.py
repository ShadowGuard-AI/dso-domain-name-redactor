import argparse
import logging
import os
import re
import sys
from faker import Faker
import chardet

# Real public suffixes recognised as domain endings. A dotted token whose
# final label is not in this set is not treated as a domain, so sentence
# joins such as "End.Start" and file names such as "file.txt" pass through.
KNOWN_TLDS = {
    "com", "net", "org", "edu", "gov", "mil", "int", "info", "biz",
    "name", "pro", "museum", "travel", "jobs", "mobi", "io", "co",
    "ai", "app", "dev", "xyz", "site", "online", "tech", "blog",
    "news", "me", "tv", "cc", "us", "uk", "eu", "de", "fr", "es",
    "it", "nl", "jp", "cn", "au", "ca", "in", "br", "mx", "se",
    "no", "fi", "dk", "pl", "be", "ch", "at", "nz", "za",
}

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
        tuple: The redacted text and the number of domain mentions redacted.
    """
    fake = Faker(language)
    # Two scope notes before the pattern. The suffix set at the top of the
    # file is a fixed list, so a real domain under a suffix it does not
    # hold is never redacted at all; the list is the whole policy. And the
    # pattern matches a domain wherever it stands, including the part of
    # an email address after the @: the local part before it is left
    # exactly as written, so an address keeps its person's name and only
    # changes its host.
    # Domain shaped tokens only: dot separated labels of letters, digits,
    # hyphens and underscores, ending in a candidate suffix. Underscores
    # are part of a label, so an underscored host name such as
    # my_host.example.com is matched as one whole token and redacted
    # whole, never in part.
    label = r"[A-Za-z0-9_](?:[A-Za-z0-9_-]*[A-Za-z0-9_])?"
    domain_pattern = (
        r"(?<![A-Za-z0-9_.\-])(" + label + r"(?:\." + label + r")*"
        r")\.([A-Za-z]{2,})(?![A-Za-z0-9_-])"
    )
    replacements = {}
    count = [0]

    def replace_domain(match):
        """Replaces the domain part while keeping the TLD.

        Returns the match unchanged when the final label is not a real
        suffix. One replacement is kept per distinct domain in a run, so
        repeated mentions are replaced the same way every time.
        """
        tld = match.group(2)
        if tld.lower() not in KNOWN_TLDS:
            return match.group(0)
        if tld != tld.lower() and tld != tld.upper():
            # A mixed case ending such as "Start" is a sentence join,
            # not a suffix.
            return match.group(0)
        key = match.group(0).lower()
        if key not in replacements:
            # Whatever its depth, a domain is replaced by exactly one fake
            # label plus its suffix: mail.corp.example.com and example.com
            # come out the same shape, and two different subdomains of one
            # parent stay distinguishable only because their full strings
            # keyed the map differently. The suffix casing stored is the
            # first occurrence's, so a later EXAMPLE.COM is rewritten with
            # the earlier mention's lowercase com.
            replacements[key] = f"{fake.domain_word()}.{tld}"
        count[0] += 1
        return replacements[key]

    redacted_text = re.sub(domain_pattern, replace_domain, text)
    return redacted_text, count[0]


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
        # Output is always utf-8, whatever encoding the input was detected
        # and read in, so a run can re-encode a file as well as redact it.
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

    if os.path.realpath(input_file) == os.path.realpath(output_file):
        logging.error(
            "Output file resolves to the input file; refusing in place run."
        )
        sys.exit(1)

    logging.info(f"Reading input file: {input_file}")
    text = read_file_content(input_file)

    if text is None:
        logging.error("Failed to read input file. Exiting.")
        sys.exit(1)

    logging.info("Redacting domain names...")
    try:
        redacted_text, redaction_count = redact_domain_name(text, language)
    except Exception as e:
        logging.error(f"Error during redaction: {e}")
        sys.exit(1)

    if redaction_count == 0:
        logging.error("No domains redacted.")
        sys.exit(1)

    logging.info(f"Writing redacted text to: {output_file}")
    write_file_content(output_file, redacted_text)

    logging.info(
        f"Domain name redaction complete. Redacted {redaction_count} domain mention(s)."
    )


if __name__ == "__main__":
    main()