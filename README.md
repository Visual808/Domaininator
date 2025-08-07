# DOMAIN-CHECKER(1) User Manual

## NAME
domain-checker - validate domain names by checking DNS resolution

## SYNOPSIS
**domain-checker** [*OPTIONS*] *INPUT_FILE* *OUTPUT_FILE*

## DESCRIPTION
**domain-checker** is a utility that validates domain names by performing DNS resolution checks. It reads domain names from an input file, checks if they exist via DNS lookup, and writes only the valid (resolvable) domains to an output file.

The tool uses concurrent processing to efficiently handle large lists of domains and includes robust error handling, retry logic, and progress indication.

## ARGUMENTS
**INPUT_FILE**
: Path to the input file containing domain names, one per line. The file should be UTF-8 encoded. Comments starting with '#' are ignored, as are empty lines.

**OUTPUT_FILE**
: Path to the output file where existing/valid domains will be saved. The file will be created if it doesn't exist, and parent directories will be created as needed.

## OPTIONS
**-t**, **--timeout** *SECONDS*
: DNS resolution timeout in seconds (default: 5.0). Increase this value if you're on a slow network connection or checking domains that may have slow DNS responses.

**-w**, **--workers** *COUNT*
: Maximum number of concurrent worker threads (default: 50). Higher values can speed up processing but may overwhelm your network connection or hit rate limits. Valid range: 1-200.

**-r**, **--retries** *COUNT*
: Number of retries for failed DNS lookups (default: 2). Failed lookups will be retried this many times before being marked as non-existent.

**-v**, **--verbose**
: Enable verbose logging output. Shows detailed information about the processing, including warnings about invalid domains and debugging information.

**--version**
: Show program version and exit.

**-h**, **--help**
: Show help message and exit.

## INPUT FILE FORMAT
The input file should contain one domain name per line. The following formats are supported:

- **example.com** - Standard domain format
- **www.example.com** - Subdomain format
- **http://example.com** - URL format (protocol will be stripped)
- **https://www.example.com/path** - Full URL (protocol and path will be stripped)
- **# This is a comment** - Comments are ignored
- *Empty lines are ignored*

### Example Input File:
```
# List of domains to check
google.com
facebook.com
www.github.com
https://stackoverflow.com
nonexistent-domain-12345.com
# End of list
```

## OUTPUT FILE FORMAT
The output file contains valid domains in alphabetical order, one per line:

```
facebook.com
github.com
google.com
stackoverflow.com
```

## EXAMPLES
**Basic usage:**
```bash
domain-checker domains.txt valid_domains.txt
```

**Check domains with custom timeout and worker count:**
```bash
domain-checker -t 10 -w 100 domains.txt filtered.txt
```

**Verbose mode with custom retry settings:**
```bash
domain-checker --verbose --retries 3 --timeout 3 input.txt output.txt
```

**Process a large file with high concurrency:**
```bash
domain-checker -w 150 -t 2 large_domain_list.txt validated.txt
```

## PERFORMANCE NOTES
- **Concurrency**: The tool uses multithreading to check multiple domains simultaneously. The default of 50 workers provides good performance for most use cases.

- **Timeout**: DNS resolution timeout affects both speed and accuracy. Lower timeouts (1-3 seconds) are faster but may miss domains with slow DNS. Higher timeouts (5-10 seconds) are more thorough but slower.

- **Network considerations**: Very high worker counts may overwhelm your network connection or trigger rate limiting by DNS servers. Start with default values and adjust as needed.

- **Memory usage**: The tool loads all domains into memory. For extremely large files (millions of domains), consider splitting the input file.

## EXIT STATUS
**0**
: Success - all domains processed successfully

**1**
: Error - file not found, permission denied, invalid arguments, or other processing error

## FILES
**/tmp/domain-checker.log**
: Log file created when verbose mode is enabled (if logging to file is configured)

## ENVIRONMENT
No special environment variables are required.

## BUGS
- Very long domain names (>253 characters) are automatically skipped as invalid
- International domain names (IDN) with non-ASCII characters may not be handled correctly in all cases
- The tool relies on system DNS resolution, so results may vary based on your DNS configuration

## SEE ALSO
**dig(1)**, **nslookup(1)**, **host(1)**, **systemd-resolve(1)**

## AUTHOR
Written by [Your Name]

## COPYRIGHT
This is free software: you are free to change and redistribute it. There is NO WARRANTY, to the extent permitted by law.

## VERSION
Domain Checker 2.0

---

## INSTALLATION
To install this script system-wide:

1. Save the script as `domain-checker` (without .py extension)
2. Make it executable: `chmod +x domain-checker`
3. Copy to a directory in your PATH: `sudo cp domain-checker /usr/local/bin/`
4. Copy this man page: `sudo cp domain-checker.1 /usr/local/share/man/man1/`
5. Update man database: `sudo mandb`

## DEPENDENCIES
- Python 3.6 or later
- tqdm package: `pip install tqdm`

Standard library modules used: socket, argparse, sys, time, concurrent.futures, pathlib, logging
