#!/usr/bin/env python3
"""
Script per eseguire i test della piattaforma KickThisUss.
"""

import os
import sys
import subprocess
import argparse


def install_test_dependencies():
    """Installa le dipendenze per i test."""
    print("📦 Installando dipendenze per i test...")
    subprocess.run([
        sys.executable, '-m', 'pip', 'install', '-r', 
        'tests/requirements-test.txt'
    ], check=True)
    print("✅ Dipendenze installate!")


def run_unit_tests():
    """Esegue i test unitari."""
    print("🧪 Eseguendo test unitari...")
    result = subprocess.run([
        'pytest', 'tests/unit/', '-v', '--tb=short'
    ])
    return result.returncode == 0


def run_integration_tests():
    """Esegue i test di integrazione."""
    print("🔗 Eseguendo test di integrazione...")
    result = subprocess.run([
        'pytest', 'tests/integration/', '-v', '--tb=short'
    ])
    return result.returncode == 0


def run_all_tests():
    """Esegue tutti i test con coverage."""
    print("🚀 Eseguendo tutti i test con coverage...")
    result = subprocess.run([
        'pytest', 'tests/', '-v', '--cov=app', '--cov-report=html', 
        '--cov-report=term-missing', '--cov-fail-under=80'
    ])
    return result.returncode == 0


def run_specific_test(test_path):
    """Esegue un test specifico."""
    print(f"🎯 Eseguendo test specifico: {test_path}")
    result = subprocess.run([
        'pytest', test_path, '-v', '--tb=long'
    ])
    return result.returncode == 0


def check_code_quality():
    """Verifica la qualità del codice."""
    print("🔍 Verificando qualità del codice...")
    
    # Black formatting
    print("📝 Controllo formatting con Black...")
    black_result = subprocess.run(['black', '--check', 'app/', 'tests/'])
    
    # Flake8 linting
    print("🔎 Controllo linting con Flake8...")
    flake8_result = subprocess.run(['flake8', 'app/', 'tests/'])
    
    # isort imports
    print("📋 Controllo import con isort...")
    isort_result = subprocess.run(['isort', '--check-only', 'app/', 'tests/'])
    
    return all(result.returncode == 0 for result in [black_result, flake8_result, isort_result])


def main():
    """Funzione principale."""
    parser = argparse.ArgumentParser(description='Test runner per KickThisUss')
    parser.add_argument('--install', action='store_true', 
                       help='Installa dipendenze test')
    parser.add_argument('--unit', action='store_true',
                       help='Esegue solo test unitari')
    parser.add_argument('--integration', action='store_true',
                       help='Esegue solo test integrazione')
    parser.add_argument('--quality', action='store_true',
                       help='Verifica qualità codice')
    parser.add_argument('--test', type=str,
                       help='Esegue test specifico')
    parser.add_argument('--all', action='store_true',
                       help='Esegue tutti i test (default)')
    
    args = parser.parse_args()
    
    if args.install:
        install_test_dependencies()
        return
    
    if args.quality:
        success = check_code_quality()
        sys.exit(0 if success else 1)
    
    if args.test:
        success = run_specific_test(args.test)
        sys.exit(0 if success else 1)
    
    if args.unit:
        success = run_unit_tests()
        sys.exit(0 if success else 1)
    
    if args.integration:
        success = run_integration_tests()
        sys.exit(0 if success else 1)
    
    # Default: tutti i test
    success = run_all_tests()
    
    if success:
        print("🎉 Tutti i test sono passati!")
        print("📊 Report coverage disponibile in htmlcov/index.html")
    else:
        print("❌ Alcuni test sono falliti!")
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
