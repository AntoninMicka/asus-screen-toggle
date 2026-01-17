# 📌 Release workflow – základní pravidla

## Význam větví
- develop
 - běžný vývoj
 - experimenty, feature větve
 - nikdy se z ní nevydává
- release/*
 - příprava vydání
 - stabilizace, ladění
 - CI ověřuje releasovatelnost
- hotfix/*
 - opravy vydaných verzí
 - CI ověřuje releasovatelnost
- main
 - obsahuje pouze vydané verze
 - každý commit odpovídá jednomu vydání
 - vždy označený tagem

- Release a hotfix větve mají tvar release/X.Y nebo hotfix/X.Y.
- Název větve neurčuje konkrétní verzi balíku.
- Konkrétní upstream verze je určena výhradně git tagem.
 
## Pravidla pro vydání
- vydání probíhá výhradně merge do main
- do main se:
 - nepushuje přímo
 - merguje se pouze přes PR
- stav v main:
 - prošel CI
 - je stabilní
 - je vhodný k vydání

- Release a hotfix větve mají tvar release/X.Y nebo hotfix/X.Y.
- CI odmítne jakoukoli větev s jiným názvem.
- Při vydání se kontroluje, že upstream verze odpovídá větvi (X.Y.Z ∈ X.Y.x).

## Tagování
- každý release commit v main:
 - má odpovídající git tag vX.Y.Z
- tagy:
 - se vytváří pouze nad main
 - nikdy nad develop nebo release/*

## Debian balení
- main je jediný zdroj pravdy pro:
 - orig.tar.gz
 - Debian source balík
- upstream tarball:
 - vzniká z git tagu
 - ne z pracovního stromu

## Automatizace (zatím neřeší detaily)
- CI:
 - ověřuje každý commit v release/* a hotfix/*
- upload:
 - probíhá lokálně z maintainerova stroje
 - po merge do main

# 🥈 CI jako gate pro release/* a hotfix/*
- Každý commit v release/* a hotfix/* musí projít CI.
- CI ověřuje, že zdroj lze zabalit a znovu rozbalit jako Debian source balík.
- Pokud CI selže, změna nesmí být mergnuta do main.

# 🥉 Lokální publish krok (maintainer-controlled release)
- Vydání balíku se provádí lokálně z počítače maintainera.
- Publish krok probíhá pouze po merge do main.
- Publish zahrnuje tagování, vytvoření Debian source balíku, podpis a upload.
- CI ani GitHub nikdy balík nepodepisují ani nenahrávají.

# 🏷️ Git tag jako jediný zdroj pravdy
- Každé vydání je identifikováno git tagem vX.Y.Z.
- Upstream tarball (orig.tar.gz) musí být vytvořen výhradně z tohoto tagu.
- Debian source balík musí odpovídat tomuto tarballu.
- Pracovní strom ani jiné větve nejsou zdrojem vydání.

# 🔢 Význam verzí (upstream vs Debian)
- Upstream verze (X.Y.Z) popisuje stav projektu a je reprezentována git tagem.
- Debian revize (-N) popisuje změny v balení a nemění upstream kód.
- Změna upstream verze vždy znamená nový tag.
- Změna Debian revize nikdy neznamená nový tag.

# 🩹 Hotfix větve a backporty
- Hotfix větve se vytvářejí z vydané verze (main / tag).
- Slouží pouze k opravám chyb ve vydaném kódu.
- Hotfix zvyšuje upstream patch verzi.
- Hotfix se po vydání merguje zpět do develop.

# 🛡️ Ochrana větví a role maintainerů
- Vydání balíků provádí pouze maintainer.
- Větev main je chráněná a obsahuje pouze vydané verze.
- Přímé pushování do main není povoleno.
- Každé vydání je vědomé rozhodnutí maintainera.

# 🔄 Chyby, opravy a rollback
- Vydané verze se nikdy nemění ani nepřepisují.
- Chyby po vydání se řeší novým vydáním (hotfix nebo nová Debian revize).
- Tagy a historie se nikdy nemažou ani nepřepisují.
- Rollback znamená vydání opravené verze, nikoli návrat v historii.
