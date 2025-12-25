#!/bin/bash
# Skript na rýchle uloženie denníka do GitHub

cd /home/narbon/Aplikácie/dennik

# Zabezpečíme, že pracujeme len so súbormi v adresári 'dennik'
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
cd "$SCRIPT_DIR" || exit 1

# Získame koreň repozitára a relatívnu cestu k tomuto adresáru
REPO_ROOT="$(git rev-parse --show-toplevel)"
TARGET_REL="$(realpath --relative-to "$REPO_ROOT" "$SCRIPT_DIR")"
TARGET_BASENAME="$(basename "$TARGET_REL" | tr '[:upper:]' '[:lower:]')"
if [ "$TARGET_BASENAME" != "dennik" ]; then
  echo "⚠️ Skript musí bežať v adresári 'dennik' (aktuálne: '$SCRIPT_DIR'). Ukončujem pre bezpečnosť."
  exit 1
fi

# Skontrolujeme veľké súbory (>100MB) a zablokujeme push ak sú prítomné
if find "$SCRIPT_DIR" -type f -size +100M -print -quit | grep -q .; then
  echo "❌ Našli sa súbory väčšie ako 100MB v adresári 'dennik'. Odstráňte alebo použite Git LFS pred pokračovaním."
  exit 1
fi

# Pridáme len zmeny v adresári dennik (relatívne k repozitáru)
git -C "$REPO_ROOT" add -A -- "$TARGET_REL"

# Commit s dátumom a časom (ak sú zmeny)
DATUM=$(date "+%Y-%m-%d %H:%M")
if git -C "$REPO_ROOT" commit -m "Záloha denníka: $DATUM"; then
  # Push na GitHub; ak vetva nemá upstream, skúšame nastaviť a opakovať
  if git -C "$REPO_ROOT" push; then
    echo ""
    echo "✅ Denník uložený do GitHub ($DATUM)"
  else
    echo "Push zlyhal, skúšam nastaviť upstream a opakovať..."
    if git -C "$REPO_ROOT" push --set-upstream origin "$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"; then
      echo ""
      echo "✅ Denník uložený do GitHub ($DATUM)"
    else
      echo ""
      echo "❌ Push zlyhal a nepodarilo sa nastaviť upstream."
      exit 1
    fi
  fi
else
  echo ""
  echo "⚠️ Žiadne zmeny na commit."
fi
