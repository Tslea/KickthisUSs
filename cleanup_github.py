#!/usr/bin/env python3
"""
Script per pulire i commit indesiderati su GitHub

ATTENZIONE: Questo script cancella PERMANENTEMENTE i commit.
Usare solo se sei sicuro!
"""

import os
import sys

print("\n" + "="*70)
print("🧹 CLEANUP GITHUB - Rimozione commit massivi")
print("="*70 + "\n")

print("⚠️  ATTENZIONE: Questa operazione cancella i commit PERMANENTEMENTE!")
print("   Usa questo script solo se:")
print("   1. I commit da cancellare contengono file non desiderati")
print("   2. Non ci sono altri collaboratori che hanno già pullato")
print("   3. Hai un backup locale del progetto")
print()

# Chiedi conferma
risposta = input("Vuoi procedere? (scrivi 'SI' per confermare): ")
if risposta != "SI":
    print("\n❌ Operazione annullata.")
    sys.exit(0)

# Chiedi quanti commit cancellare
print("\n📊 Vai su GitHub e controlla quanti commit vuoi cancellare:")
print("   https://github.com/Tslea/KickthisUSs/commits/main")
print()

try:
    n_commits = int(input("Quanti commit vuoi cancellare? (es: 600): "))
except ValueError:
    print("\n❌ Numero non valido.")
    sys.exit(1)

if n_commits <= 0:
    print("\n❌ Il numero deve essere positivo.")
    sys.exit(1)

print(f"\n🔄 Preparo i comandi per cancellare {n_commits} commit...")
print("\n" + "="*70)
print("COMANDI DA ESEGUIRE:")
print("="*70 + "\n")

print("# 1. Clona il repository (se non l'hai già fatto)")
print("git clone https://github.com/Tslea/KickthisUSs.git")
print("cd KickthisUSs")
print()

print("# 2. Resetta ai commit precedenti")
print(f"git reset --hard HEAD~{n_commits}")
print()

print("# 3. Forza il push (ATTENZIONE: cancella definitivamente i commit)")
print("git push --force origin main")
print()

print("="*70)
print("\n⚠️  IMPORTANTE:")
print("   - Questi comandi cancellano PERMANENTEMENTE i commit")
print("   - Se altri hanno pullato, creerai problemi di sync")
print("   - Esegui i comandi nel terminale Git Bash o PowerShell")
print()

print("✅ Se vuoi procedere, copia i comandi sopra ed eseguili manualmente.")
print()
