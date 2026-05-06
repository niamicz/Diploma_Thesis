Diplomová práce

Ultrazvukový anemometr s kompenzací vlivů prostředíTento repozitář obsahuje kompletní zdrojové kódy a technickou dokumentaci k diplomové práci autora Jakuba Švrčka (Univerzita obrany, 2026). Cílem projektu byl návrh a realizace funkčního prototypu anemometru postaveného na platformě ESP32.  

📂 Struktura repozitáře/firmware – Zdrojový kód pro mikrokontrolér ESP32 (C++/Arduino IDE).  Obsahuje algoritmy pro simultánní buzení, měření Time-of-Flight a webový server.  /python_app – Diagnostická a logovací aplikace v jazyce Python.  Nástroje pro vizualizaci dat, výpočet průměrů a export do .csv.  /simulation – Numerické simulace aerodynamického stínění věží (metoda LBM).  /data – Ukázkové soubory naměřených dat z terénních a laboratorních testů.  /docs – Schémata zapojení a fotodokumentace prototypu.  

🛠️ Použitý hardware ESP32-WROOM-32 – Hlavní výpočetní jednotka s integrovanou Wi-Fi.  HY-SR05 (4x) – Ultrazvukové moduly pro měření doby letu impulsu.  BMP280 – Environmentální senzor pro kompenzaci teploty a tlaku.  

🚀 Klíčové funkce Asymetrický multiprocesting (AMP) – Separace kritického měření od komunikace.  Dynamická kompenzace – Automatická úprava rychlosti zvuku na základě dat z BMP280.  Mitigace stínění – Algoritmus pro potlačení systematické chyby způsobené konstrukcí.  Webové rozhraní – Real-time vizualizace vektorů větru skrze integrovaný AP.  
