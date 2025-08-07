#!/usr/bin/env python3
"""
Domain Existence Checker

A utility script to validate domain names by checking their DNS resolution.
Reads domain names from an input file, checks if they exist via DNS lookup,
and writes valid domains to an output file.

Version: 2.0
License: MIT
"""

import socket
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple, Optional
import logging
from tqdm import tqdm

class DomainChecker:
    """
    A class to handle domain validation operations with improved performance
    and error handling capabilities.
    """
    
    def __init__(self, timeout: float = 5.0, max_workers: int = 50, retry_count: int = 2):
        """
        Initialize the DomainChecker with configuration parameters.
        
        Args:
            timeout: DNS resolution timeout in seconds (default: 5.0)
            max_workers: Maximum number of concurrent threads (default: 50)
            retry_count: Number of retries for failed lookups (default: 2)
        """
        self.timeout = timeout
        self.max_workers = max_workers
        self.retry_count = retry_count
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def domain_exists(self, domain: str) -> Tuple[str, bool]:
        """
        Check if a domain exists by attempting to resolve it via DNS.
        
        Uses socket.gethostbyname() for DNS resolution with timeout and retry logic.
        This method is more reliable than simple ping checks as it specifically
        tests DNS resolution.
        
        Args:
            domain: The domain name to check (without protocol prefix)
            
        Returns:
            Tuple of (domain, exists_flag) where exists_flag is True if domain resolves
            
        Examples:
            >>> checker = DomainChecker()
            >>> checker.domain_exists("google.com")
            ('google.com', True)
            >>> checker.domain_exists("nonexistent-domain-12345.com")
            ('nonexistent-domain-12345.com', False)
        """
        domain = domain.strip().lower()
        
        # Basic domain format validation
        if not domain or '.' not in domain or len(domain) > 253:
            return (domain, False)
        
        # Remove common protocol prefixes if present
        for prefix in ['http://', 'https://', 'www.']:
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
        
        # Remove trailing path/query parameters
        domain = domain.split('/')[0].split('?')[0]
        
        # Attempt DNS resolution with retries
        for attempt in range(self.retry_count + 1):
            try:
                # Set socket timeout for DNS resolution
                old_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(self.timeout)
                
                # Perform DNS lookup
                socket.gethostbyname(domain)
                socket.setdefaulttimeout(old_timeout)
                
                return (domain, True)
                
            except socket.gaierror as e:
                # DNS resolution failed - domain likely doesn't exist
                socket.setdefaulttimeout(old_timeout)
                return (domain, False)
                
            except socket.timeout:
                # Timeout occurred - retry if attempts remaining
                socket.setdefaulttimeout(old_timeout)
                if attempt < self.retry_count:
                    time.sleep(0.5)  # Brief pause before retry
                    continue
                return (domain, False)
                
            except Exception as e:
                # Unexpected error - log and mark as non-existent
                socket.setdefaulttimeout(old_timeout)
                self.logger.debug(f"Unexpected error checking {domain}: {e}")
                return (domain, False)
        
        return (domain, False)
    
    def load_domains_from_file(self, input_file: Path) -> List[str]:
        """
        Load and validate domain list from input file.
        
        Reads domains from file, strips whitespace, removes duplicates,
        and filters out empty lines and basic invalid entries.
        
        Args:
            input_file: Path to file containing domain names (one per line)
            
        Returns:
            List of cleaned domain names
            
        Raises:
            FileNotFoundError: If input file doesn't exist
            PermissionError: If file can't be read due to permissions
            UnicodeDecodeError: If file contains invalid characters
        """
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                domains = []
                for line_num, line in enumerate(f, 1):
                    domain = line.strip()
                    
                    # Skip empty lines and comments
                    if not domain or domain.startswith('#'):
                        continue
                    
                    # Basic validation
                    if len(domain) > 253:
                        self.logger.warning(f"Line {line_num}: Domain too long (>253 chars): {domain[:50]}...")
                        continue
                    
                    domains.append(domain)
                
                # Remove duplicates while preserving order
                unique_domains = list(dict.fromkeys(domains))
                
                if len(domains) != len(unique_domains):
                    self.logger.info(f"Removed {len(domains) - len(unique_domains)} duplicate domains")
                
                return unique_domains
                
        except FileNotFoundError:
            raise FileNotFoundError(f"Input file '{input_file}' not found")
        except PermissionError:
            raise PermissionError(f"Permission denied reading '{input_file}'")
        except UnicodeDecodeError as e:
            raise UnicodeDecodeError(f"File encoding error in '{input_file}': {e}")
    
    def save_domains_to_file(self, domains: List[str], output_file: Path) -> None:
        """
        Save valid domains to output file.
        
        Args:
            domains: List of valid domain names to save
            output_file: Path where to save the domains
            
        Raises:
            PermissionError: If output file can't be written
            OSError: If disk space or other OS-level error occurs
        """
        try:
            # Create parent directories if they don't exist
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                for domain in sorted(domains):  # Sort for consistent output
                    f.write(f"{domain}\n")
                    
            self.logger.info(f"Successfully wrote {len(domains)} domains to {output_file}")
            
        except PermissionError:
            raise PermissionError(f"Permission denied writing to '{output_file}'")
        except OSError as e:
            raise OSError(f"Failed to write to '{output_file}': {e}")
    
    def check_domains_concurrent(self, domains: List[str]) -> List[str]:
        """
        Check domain existence using concurrent processing for improved performance.
        
        Uses ThreadPoolExecutor to check multiple domains simultaneously,
        significantly reducing total processing time for large domain lists.
        
        Args:
            domains: List of domain names to check
            
        Returns:
            List of domains that exist (resolve via DNS)
        """
        existing_domains = []
        
        # Use ThreadPoolExecutor for concurrent DNS lookups
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all domain check tasks
            future_to_domain = {
                executor.submit(self.domain_exists, domain): domain 
                for domain in domains
            }
            
            # Process results as they complete with progress bar
            with tqdm(total=len(domains), desc="Checking domains", unit="domain") as pbar:
                for future in as_completed(future_to_domain):
                    domain, exists = future.result()
                    if exists:
                        existing_domains.append(domain)
                    pbar.update(1)
        
        return existing_domains
    
    def filter_existing_domains(self, input_file: Path, output_file: Path) -> None:
        """
        Main processing function to filter existing domains from input to output file.
        
        Orchestrates the complete workflow:
        1. Load domains from input file
        2. Check domain existence concurrently
        3. Save valid domains to output file
        4. Display summary statistics
        
        Args:
            input_file: Path to input file containing domains
            output_file: Path to output file for valid domains
            
        Raises:
            Various exceptions from underlying methods (file I/O, network, etc.)
        """
        try:
            # Load domains from input file
            self.logger.info(f"Loading domains from {input_file}")
            domains = self.load_domains_from_file(input_file)
            
            if not domains:
                print("❌ No valid domains found in input file")
                return
            
            print(f"📋 Loaded {len(domains)} domains for validation")
            
            # Check domain existence
            start_time = time.time()
            existing_domains = self.check_domains_concurrent(domains)
            end_time = time.time()
            
            # Save results
            if existing_domains:
                self.save_domains_to_file(existing_domains, output_file)
                
                # Display summary
                print(f"\n✅ Results Summary:")
                print(f"   Total domains checked: {len(domains)}")
                print(f"   Existing domains found: {len(existing_domains)}")
                print(f"   Invalid/non-existent: {len(domains) - len(existing_domains)}")
                print(f"   Processing time: {end_time - start_time:.2f} seconds")
                print(f"   Output saved to: {output_file}")
            else:
                print(f"\n⚠️  No existing domains found out of {len(domains)} checked")
                
        except Exception as e:
            self.logger.error(f"Error processing domains: {e}")
            print(f"❌ Error: {e}")
            sys.exit(1)


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure command-line argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Validate domain names by checking DNS resolution",
        epilog="""
Examples:
  %(prog)s domains.txt valid_domains.txt
  %(prog)s -t 10 -w 100 input.txt output.txt
  %(prog)s --verbose --timeout 3 domains.txt filtered.txt

Input file format:
  One domain per line, comments start with #
  Supports domains with or without www/http prefixes
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "input_file",
        type=Path,
        help="Input file containing domain names (one per line)"
    )
    
    parser.add_argument(
        "output_file", 
        type=Path,
        help="Output file for existing/valid domains"
    )
    
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=5.0,
        help="DNS resolution timeout in seconds (default: 5.0)"
    )
    
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=50,
        help="Maximum concurrent workers (default: 50)"
    )
    
    parser.add_argument(
        "-r", "--retries",
        type=int,
        default=2,
        help="Number of retries for failed lookups (default: 2)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Domain Checker 2.0"
    )
    
    return parser


def main() -> None:
    """
    Main entry point for the domain checker utility.
    
    Parses command-line arguments and executes domain validation workflow.
    """
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate arguments
    if not args.input_file.exists():
        print(f"❌ Input file '{args.input_file}' does not exist")
        sys.exit(1)
    
    if args.timeout <= 0:
        print("❌ Timeout must be positive")
        sys.exit(1)
    
    if args.workers <= 0 or args.workers > 200:
        print("❌ Workers must be between 1 and 200")
        sys.exit(1)
    
    # Initialize checker and process domains
    checker = DomainChecker(
        timeout=args.timeout,
        max_workers=args.workers,
        retry_count=args.retries
    )
    
    checker.filter_existing_domains(args.input_file, args.output_file)


if __name__ == "__main__":
    main()
