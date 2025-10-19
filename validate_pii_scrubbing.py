#!/usr/bin/env python3
"""
Validation script to ensure PII scrubbing was successful and comprehensive.
Checks for remaining PII patterns and validates code functionality.
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Tuple

def check_remaining_pii(project_dir: Path) -> Dict[str, List[Tuple[str, int, str]]]:
    """
    Check for any remaining PII patterns that might have been missed.
    Returns dict of {file_path: [(pattern_type, line_number, context)]}
    """
    
    # Define PII patterns to check for
    pii_patterns = {
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'phone': r'\b\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
        'ssn': r'\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b',
        'personal_name_ryan': r'\bRyan\b',
        'personal_name_thomson': r'\bthomson\b',
        'api_key': r'(?:api[_-]?key|token|secret)[\s]*[=:]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
        'github_token': r'gh[ps]_[a-zA-Z0-9]{36}',
        'address': r'\b\d{1,5}\s+[A-Za-z\s]{3,}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct)\s+(?:Apt|Suite|Unit)?\s*\d*\b'
    }
    
    # Allowed patterns (these should not be flagged)
    allowed_patterns = [
        r'user@example\.com',  # Our replacement email
        r'github\.com/thebearwithabite',  # GitHub repo references are OK
        r'XXX-XXX-XXXX',  # Our replacement phone
        r'User',  # Generic user replacement
        r'user',  # Generic user replacement
        r'\[REDACTED_.*\]',  # Our redacted tokens
        r'v\d+\.\d+',  # Version numbers like v2.0
        r'system #\d+',  # System numbers like system #8
        r'up to \d+ ',  # Phrases like "up to 5 most recent"
        r'\d+ test files',  # Technical references
        r'\d+ Bad Request',  # HTTP status codes
    ]
    
    findings = {}
    
    # Check all relevant files
    file_patterns = ['*.py', '*.md', '*.txt', '*.json', '*.yml', '*.yaml']
    files_to_check = []
    
    for pattern in file_patterns:
        files_to_check.extend(project_dir.glob(pattern))
        # Check subdirectories too
        for subdir in project_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith('.'):
                files_to_check.extend(subdir.glob(pattern))
    
    for file_path in files_to_check:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            file_findings = []
            
            for line_num, line in enumerate(lines, 1):
                # Check each PII pattern
                for pattern_name, pattern in pii_patterns.items():
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    
                    for match in matches:
                        matched_text = match.group(0)
                        
                        # Check if this is an allowed pattern
                        is_allowed = False
                        
                        # Check against allowed patterns
                        for allowed_pattern in allowed_patterns:
                            if re.search(allowed_pattern, matched_text, re.IGNORECASE):
                                is_allowed = True
                                break
                        
                        # Additional context-based filtering for address pattern
                        if pattern_name == 'address' and not is_allowed:
                            # Skip if it's clearly not a real address
                            if any(word in line.lower() for word in ['specification', 'version', 'system', 'file', 'exceed', 'implement', 'document']):
                                is_allowed = True
                        
                        if not is_allowed:
                            context = line.strip()
                            file_findings.append((pattern_name, line_num, context))
            
            if file_findings:
                findings[str(file_path.relative_to(project_dir))] = file_findings
                
        except Exception as e:
            print(f"❌ Error checking {file_path}: {e}")
    
    return findings

def validate_code_functionality(project_dir: Path) -> List[str]:
    """
    Basic validation that Python files can still be imported/parsed.
    Returns list of issues found.
    """
    issues = []
    
    python_files = list(project_dir.glob('*.py'))
    
    for py_file in python_files:
        try:
            # Check syntax by compiling
            with open(py_file, 'r', encoding='utf-8') as f:
                source = f.read()
            
            compile(source, str(py_file), 'exec')
            
        except SyntaxError as e:
            issues.append(f"Syntax error in {py_file.name}: {e}")
        except Exception as e:
            issues.append(f"Issue with {py_file.name}: {e}")
    
    return issues

def main():
    """Run PII validation"""
    
    print("🔍 Validating PII Scrubbing Results")
    print("=" * 50)
    
    project_dir = Path(os.getcwd())
    
    # Check for remaining PII
    print("🕵️  Checking for remaining PII patterns...")
    remaining_pii = check_remaining_pii(project_dir)
    
    if remaining_pii:
        print(f"⚠️  Found {len(remaining_pii)} files with potential remaining PII:")
        for file_path, findings in remaining_pii.items():
            print(f"\n📄 {file_path}:")
            for pattern_type, line_num, context in findings:
                print(f"   Line {line_num} ({pattern_type}): {context[:80]}...")
    else:
        print("✅ No remaining PII patterns detected!")
    
    # Validate code functionality
    print(f"\n🔧 Validating code syntax...")
    syntax_issues = validate_code_functionality(project_dir)
    
    if syntax_issues:
        print(f"❌ Found {len(syntax_issues)} syntax issues:")
        for issue in syntax_issues:
            print(f"   - {issue}")
    else:
        print("✅ All Python files have valid syntax!")
    
    # Summary
    print(f"\n📊 Validation Summary:")
    print(f"   Files with remaining PII: {len(remaining_pii)}")
    print(f"   Syntax issues found: {len(syntax_issues)}")
    
    if not remaining_pii and not syntax_issues:
        print("\n🎉 PII scrubbing validation PASSED!")
        print("✅ Repository is clean and ready for public release")
        return True
    else:
        print("\n⚠️  PII scrubbing validation found issues")
        print("🔧 Please review and address the findings above")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)