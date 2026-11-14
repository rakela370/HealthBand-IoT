KOMPLETNA SPECIFIKACIJA DIPLOMSKOG PROJEKTA

Naziv projekta:
PROJEKTOVANJE I IMPLEMENTACIJA MODULARNE ARHITEKTURE SIMULIRANOG WEARABLE IoT UREĐAJA ZA PRcije:
1.0

Datum:
15. jul 2026.

Student:
Nikola Rakić, RA64/2022

Status dokumenta:
Prijedlog kompletne specifikacije koji treba predstaviti profesorici i potvrditi prije početka implementacije.

======================================================================

1. NAMJENA OVOG DOKUMENTA
   ======================================================================

Ovaj dokument predstavlja kompletnu tehničku i funkcionalnu specifikaciju diplomskog projekta.

Dokument treba koristiti kao glavni izvor informacija tokom cijelog razvoja projekta. Napisan je tako da se može:

* sačuvati kao tekstualni fajl;
* poslati profesorici radi objašnjenja zamišljene teme;
* poslati u novi ChatGPT ili drugi AI thread;
* koristiti za planiranje implementacije;
* koristiti kao osnova za pisanje diplomskog rada;
* koristiti za provjeru da nijedan zahtjev profesorice nije izostavljen.

AI asistent koji dobije ovaj dokument treba da ga posmatra kao glavni izvor istine o projektu. Arhitekturu, tehnologije i obim projekta ne treba samovoljno mijenjati, osim ako student naknadno prenese izmjene koje je zahtijevala profesorica.

======================================================================
2. ZAHTJEVI PROFESORICE KOJE PROJEKAT MORA ISPUNITI
===================================================

Profesorica očekuje projekat koji prikazuje opštu arhitekturu pametnog IoT uređaja povezanog sa cloud platformom.

Projekat mora demonstrirati sljedeće:

1. Simulaciju IoT uređaja.

Uređaj ne mora biti fizički napravljen i nije potrebno povezivanje sa stvarnim hardverskim senzorima. Međutim, simulirani uređaj mora imati jasno definisano ponašanje, mora znati u kojem se stanju nalazi i mora generisati senzorske vrijednosti u skladu sa aktivnim simulacionim scenarijem.

2. Povezivanje sa AWS IoT Core platformom.

Simulirani uređaj mora se povezivati sa AWS IoT Core servisom i razmjenjivati podatke sa cloudom.

3. MQTT komunikaciju.

Za komunikaciju između uređaja i AWS IoT Core platforme koristiće se MQTT protokol.

4. Enkriptovanu komunikaciju.

MQTT komunikacija mora se izvršavati preko TLS-a.

5. Autentikaciju uređaja.

Uređaj mora imati svoj identitet i autentifikovati se prilikom povezivanja. Planirano je korišćenje X.509 klijentskog sertifikata i privatnog ključa.

6. Prijavljivanje promjena stanja uređaja.

Uređaj mora slati informacije o svom trenutnom stanju, promjenama režima rada, upozorenjima, kvarovima senzora, stanju baterije, verziji softvera i drugim važnim događajima.

7. Prihvatanje komandi.

Uređaj mora prihvatati komande koje dolaze sa korisničke aplikacije, izvršavati ih i vraćati rezultat izvršenja.

8. Daljinsku konfiguraciju funkcionalnosti.

Sa korisničke aplikacije mora biti moguće mijenjati parametre uređaja, kao što su:

* period očitavanja senzora;
* period slanja telemetrije;
* period lokalne agregacije;
* temperaturna jedinica, Celzijus ili Farenhajt;
* pragovi za generisanje upozorenja;
* uključivanje ili isključivanje određenih upozorenja.

9. Simulirano očitavanje senzora.

Uređaj mora simulirati više senzorskih vrijednosti koje su povezane sa zdravstvenim stanjem ili aktivnošću korisnika.

10. Lokalnu analitiku na uređaju.

Uređaj ne treba samo prosljeđivati sirove podatke u cloud. Na samom uređaju mora postojati analitički modul koji obrađuje prikupljena mjerenja, na primjer računajući srednju, minimalnu i maksimalnu vrijednost tokom definisanog vremenskog intervala.

11. Prikupljanje i čuvanje podataka u cloudu.

Podaci poslati sa uređaja moraju se sačuvati kako bi korisnička aplikacija mogla prikazivati istoriju mjerenja.

12. Prikaz istorije.

Korisnička aplikacija mora omogućiti prikaz istorijskih podataka, uključujući podatke za prethodnih 30 dana.

13. OTA nadogradnju.

Mora se implementirati Over-the-Air mehanizam koji uređaju omogućava da daljinski primi novu softversku verziju.

14. Dodavanje nove funkcionalnosti nakon OTA nadogradnje.

OTA ne smije biti samo promjena teksta koji prikazuje broj verzije. Nakon nadogradnje uređaj mora dobiti stvarnu novu funkcionalnost, kao što je podrška za novi simulirani senzor i nova vrsta analitike.

15. Modularnu arhitekturu uređaja.

Program uređaja mora biti podijeljen na zasebne module, uključujući najmanje:

* glavnu logiku uređaja;
* komunikacioni modul;
* modul za očitavanje senzora;
* modul za izvršavanje komandi;
* konfiguracioni modul;
* modul za lokalnu analitiku;
* modul za monitoring zdravlja samog uređaja;
* OTA modul.

16. Monitoring zdravlja uređaja.

Mora se pratiti tehničko zdravlje samog uređaja. Ovo nije isto što i praćenje zdravstvenih parametara korisnika.

17. Mogućnost proširenja lokalne analitike korišćenjem AWS IoT Greengrass servisa.

Greengrass je profesorica navela kao jednu od opcija, a ne kao strogo obavezan dio. Osnovna lokalna analitika biće implementirana u samom Python programu. Greengrass se može dodati kao napredno proširenje ako vrijeme i AWS nalog to dozvole ili ako ga profesorica izričito zatraži.

======================================================================
3. OSNOVNA IDEJA PROJEKTA
=========================

Biće napravljen simulirani wearable IoT uređaj koji predstavlja pametnu narukvicu za praćenje zdravstvenih i aktivnosti parametara korisnika.

Uređaj će se zvati HealthBand.

Primjer identifikatora uređaja:

healthband-device-001

HealthBand neće biti fizički hardverski uređaj. Biće implementiran kao modularna Python aplikacija koja se na računaru ponaša kao stvaran IoT uređaj.

Uređaj će:

* simulirati senzore;
* znati svoje trenutno stanje;
* simulirati različite aktivnosti korisnika;
* periodično očitavati senzore;
* lokalno analizirati očitavanja;
* generisati upozorenja;
* slati telemetriju u AWS IoT Core;
* primati konfiguraciju;
* primati jednokratne komande;
* čuvati podatke kada nema internet veze;
* sinhronizovati zaostale podatke nakon ponovnog povezivanja;
* pratiti stanje baterije;
* pratiti tehničko stanje senzora;
* pratiti stanje MQTT veze;
* primati OTA softversku nadogradnju;
* nakon OTA nadogradnje dobiti novi tip mjerenja i novu analitiku.

Korisnička aplikacija biće web aplikacija koja u internet browseru prikazuje:

* vizuelnu simulaciju pametne narukvice;
* trenutna mjerenja;
* stanje uređaja;
* istorijske grafikone;
* upozorenja;
* konfiguraciju;
* komande;
* status senzora;
* status MQTT veze;
* status OTA nadogradnje.

======================================================================
4. VAŽNA GRANICA PROJEKTA
=========================

HealthBand je simulirani edukativni IoT sistem, a ne medicinski uređaj.

Sistem:

* ne postavlja dijagnozu;
* ne predlaže terapiju;
* ne donosi medicinske odluke;
* ne koristi podatke stvarnih pacijenata;
* ne tvrdi da su simulirana mjerenja klinički precizna;
* ne kontaktira zdravstvene ustanove;
* ne poziva hitnu pomoć.

Svi podaci biće sintetički i generisani u okviru simulacije.

Pragovi upozorenja služiće isključivo za demonstraciju konfiguracije, lokalne analitike i generisanja događaja. Oni neće biti predstavljeni kao medicinski validirani pragovi.

Na korisničkom interfejsu treba jasno pisati:

„Svi prikazani podaci su simulirani. Sistem nije medicinski uređaj.“

======================================================================
5. GLAVNI CILJ DIPLOMSKOG RADA
==============================

Glavni cilj rada nije samo prikazivanje simuliranog pulsa.

Glavni cilj je projektovanje, implementacija i demonstracija opšte modularne arhitekture pametnog IoT uređaja koji:

* prikuplja podatke;
* lokalno obrađuje podatke;
* sigurno komunicira sa cloudom;
* prima komande;
* prima konfiguraciju;
* prijavljuje svoje stanje;
* funkcioniše i tokom privremenog prekida interneta;
* čuva istorijske podatke;
* može se daljinski softverski nadograditi.

Wearable uređaj za praćenje zdravstvenog stanja koristi se kao konkretan primjer na kojem se prikazuje takva opšta arhitektura.

======================================================================
6. GLAVNE KOMPONENTE SISTEMA
============================

Kompletan sistem biće podijeljen na četiri glavne cjeline:

1. SIMULATOR WEARABLE UREĐAJA

Modularna Python aplikacija koja predstavlja sam HealthBand uređaj.

2. AWS CLOUD INFRASTRUKTURA

AWS servisi koji omogućavaju MQTT komunikaciju, autentikaciju, konfiguraciju, čuvanje podataka, OTA nadogradnju i monitoring.

3. KORISNIČKI WEB BACKEND

Python FastAPI aplikacija koja povezuje web interfejs sa AWS servisima.

4. KORISNIČKI WEB FRONTEND

HTML, CSS i JavaScript aplikacija koja prikazuje podatke, grafikone, animacije i kontrole.

Pojednostavljena arhitektura:

SIMULIRANI HEALTHBAND UREĐAJ
|
| MQTT preko TLS-a
| X.509 sertifikat
|
v
AWS IoT CORE
|
|-- Device Shadow
|-- IoT Rules
|-- IoT Jobs
|
|-------------------> Amazon DynamoDB
|                     istorijski podaci
|
|-------------------> Amazon S3
|                     OTA paketi
|
|-------------------> Amazon CloudWatch
logovi i monitoring

FASTAPI WEB BACKEND
|
| AWS API + MQTT
|
v
AWS SERVISI

WEB BROWSER
|
| REST API + WebSocket
|
v
FASTAPI BACKEND

======================================================================
7. IZABRANI JEZICI, ALATI I PLATFORME
=====================================

7.1. Programski jezik simulatora uređaja

Koristiće se:

Python 3

Preporučena verzija:

Python 3.12 ili novija kompatibilna verzija.

Python se koristi zato što:

* uređaj nije fizički mikrokontroler;
* omogućava brzu implementaciju simulacije;
* pogodan je za modularnu arhitekturu;
* podržava asinhroni rad;
* lako obrađuje JSON podatke;
* lako implementira lokalnu analitiku;
* postoji AWS IoT Device SDK za Python;
* omogućava jednostavnu implementaciju OTA mehanizma nad Python modulima.

7.2. AWS biblioteka za simulirani uređaj

Koristiće se:

AWS IoT Device SDK for Python v2

Python paket:

awsiotsdk

SDK će se koristiti za:

* MQTT povezivanje sa AWS IoT Core;
* TLS komunikaciju;
* objavljivanje MQTT poruka;
* pretplaćivanje na MQTT topic-e;
* rad sa Device Shadow mehanizmom;
* rad sa AWS IoT Jobs mehanizmom.

7.3. Web backend

Koristiće se:

* Python;
* FastAPI;
* Uvicorn;
* boto3;
* Pydantic;
* AWS IoT Device SDK za posebnu MQTT konekciju web aplikacije.

FastAPI backend će:

* davati REST API frontend aplikaciji;
* održavati WebSocket konekcije;
* preuzimati podatke iz DynamoDB baze;
* objavljivati komande uređaju;
* mijenjati željenu konfiguraciju u Device Shadow dokumentu;
* pokretati AWS IoT Job za OTA nadogradnju;
* primati MQTT podatke u realnom vremenu;
* prosljeđivati promjene browseru preko WebSocket-a.

7.4. Web frontend

Koristiće se:

* HTML5;
* CSS3;
* JavaScript;
* SVG;
* Chart.js.

Neće se koristiti React, Angular ili Vue u osnovnoj verziji, jer za ovaj projekat nisu neophodni i povećali bi količinu frontend posla.

HTML će definisati strukturu stranica.

CSS će se koristiti za:

* moderan izgled;
* raspored elemenata;
* kartice;
* animacije;
* prikaz pametne narukvice;
* animaciju srca;
* upozorenja;
* OTA progress bar;
* responsive prikaz.

JavaScript će se koristiti za:

* primanje podataka preko WebSocket-a;
* ažuriranje prikaza bez osvježavanja stranice;
* slanje REST zahtjeva backendu;
* ažuriranje grafikona;
* promjenu aktivnih CSS klasa;
* pokretanje animacija;
* prikaz nove SpO2 kartice nakon OTA nadogradnje.

SVG će se koristiti za:

* prikaz pametne narukvice;
* ikone;
* animiranu liniju pulsa;
* prikaz senzora;
* druge grafičke elemente.

Chart.js će se koristiti za:

* grafikon pulsa;
* grafikon temperature;
* grafikon koraka;
* grafikon baterije;
* grafikon SpO2 nakon OTA nadogradnje;
* istorijske podatke;
* agregirane podatke.

7.5. Lokalna baza uređaja

Koristiće se:

SQLite

SQLite će se koristiti za:

* privremeno čuvanje mjerenja tokom prekida internet veze;
* offline red poruka;
* čuvanje događaja koji još nisu poslati u cloud;
* čuvanje lokalnog stanja potrebnog nakon restarta uređaja.

Za osnovnu implementaciju može se koristiti ugrađeni Python modul sqlite3.

7.6. Cloud baza

Koristiće se:

Amazon DynamoDB

DynamoDB će čuvati:

* telemetriju;
* agregirane podatke;
* upozorenja;
* događaje;
* istoriju stanja uređaja.

7.7. OTA skladište

Koristiće se:

Amazon S3

S3 će čuvati:

* ZIP pakete softverskih verzija;
* manifest fajlove;
* eventualne potpise ili hash vrijednosti;
* job dokumente ako bude potrebno.

S3 bucket mora biti privatan.

7.8. OTA upravljanje

Koristiće se:

AWS IoT Jobs

AWS IoT Jobs će:

* obavijestiti uređaj o dostupnoj nadogradnji;
* prenijeti uređaju job dokument;
* omogućiti uređaju da prijavljuje napredak;
* evidentirati uspjeh ili neuspjeh nadogradnje.

7.9. Daljinska konfiguracija

Koristiće se:

AWS IoT Device Shadow

Device Shadow će sadržati:

* desired konfiguraciju koju želi korisnička aplikacija;
* reported konfiguraciju koju je uređaj stvarno primijenio;
* informacije o verziji;
* informacije o podržanim funkcionalnostima;
* trenutno logičko stanje uređaja.

Device Shadow se neće koristiti za često slanje senzorske telemetrije. Telemetrija će se slati preko posebnih MQTT topic-a.

7.10. Cloud routing

Koristiće se:

AWS IoT Rules

IoT Rules će:

* slušati odgovarajuće MQTT topic-e;
* izdvajati podatke iz JSON poruka;
* upisivati podatke u DynamoDB;
* po potrebi slati određene logove u CloudWatch.

7.11. Logging i monitoring

Koristiće se:

* Python logging;
* Amazon CloudWatch Logs;
* lokalni tekstualni log fajlovi.

7.12. Razvojno okruženje

Preporučeno:

* Windows ili WSL2 na Windowsu posto nemam dual boot;
* Visual Studio Code;
* Git;
* GitHub privatni ili javni repozitorijum bez tajnih podataka;
* AWS CLI;
* Python virtual environment;
* Postman, opciono, za testiranje REST API-ja.

7.13. Testiranje

Koristiće se:

* pytest;
* pytest-asyncio;
* HTTPX za FastAPI testove;
* ručni integracioni testovi;
* AWS IoT MQTT test client;
* AWS CloudWatch logovi.

7.14. Upravljanje zavisnostima

Koristiće se:

* Python venv;
* requirements.txt.

Minimalne Python zavisnosti vjerovatno će uključivati:

* awsiotsdk;
* boto3;
* fastapi;
* uvicorn;
* pydantic;
* pydantic-settings;
* python-dotenv;
* aiofiles;
* psutil;
* pytest;
* pytest-asyncio;
* httpx.

Tačne verzije biblioteka treba zaključati u requirements.txt fajlu kada se napravi početno radno okruženje.

======================================================================
8. AWS NALOG I PREDUSLOVI
=========================

Prije implementacije mora se provjeriti da li studentski ili drugi dostupan AWS nalog omogućava korišćenje sljedećih servisa:

* AWS IoT Core;
* AWS IoT Device Management;
* AWS IoT Jobs;
* AWS IoT Device Shadow;
* Amazon DynamoDB;
* Amazon S3;
* Amazon CloudWatch;
* AWS IAM;
* AWS IoT Greengrass, ako se bude implementirao.

Sve resurse treba napraviti u istoj AWS regiji.

Moguća regija:

eu-central-1

Konačna regija biće izabrana nakon provjere dostupnosti servisa na konkretnom nalogu.

Potrebno je postaviti budžetsko upozorenje ili drugi način kontrole troškova.

Ako studentski nalog ne podržava neki obavezni servis, problem prvo treba prijaviti profesorici prije zamjene AWS servisa alternativom.

Greengrass nije obavezan za osnovnu verziju projekta.

======================================================================
9. SIMULIRANI SENZORI U VERZIJI 1.0
===================================

Početna softverska verzija uređaja biće:

1.0.0

Verzija 1.0.0 podržavaće sljedeće simulirane senzore i vrijednosti.

9.1. Senzor srčane frekvencije

Naziv:

HeartRateSensor

Mjerena vrijednost:

heartRateBpm

Jedinica:

BPM, otkucaji u minuti.

Senzor će generisati vrijednosti u skladu sa trenutnom aktivnošću simuliranog korisnika.

Vrijednosti se neće mijenjati potpuno nasumično. Koristiće se:

* ciljna vrijednost prema scenariju;
* postepeno približavanje ciljnoj vrijednosti;
* mala slučajna odstupanja;
* filtriranje naglih nerealnih skokova;
* mogućnost namjernog generisanja greške.

9.2. Senzor temperature kože

Naziv:

SkinTemperatureSensor

Mjerena vrijednost:

skinTemperature

Podržane jedinice:

* CELSIUS;
* FAHRENHEIT.

Uređaj će interno koristiti Celzijus kao kanonsku jedinicu.

Na osnovu konfiguracije, vrijednost će prije slanja biti:

* prijavljena u Celzijusima;
* ili konvertovana i prijavljena u Farenhajtima.

Svaka poruka mora sadržati i vrijednost i jedinicu.

Primjer:

"skinTemperature": 33.8
"temperatureUnit": "CELSIUS"

9.3. Senzor koraka

Naziv:

StepCounterSensor

Vrijednosti:

* stepsInInterval;
* totalDailySteps.

Broj koraka zavisiće od aktivnog scenarija.

Tokom mirovanja broj koraka će biti nula ili veoma mali.

Tokom hodanja broj koraka će rasti umjerenom brzin om.

Tokom trčanja broj koraka će rasti znatno brže.

9.4. Nivo aktivnosti

Naziv:

ActivitySensor ili ActivityClassifier

Moguće vrijednosti:

* SLEEPING;
* RESTING;
* LIGHT;
* MODERATE;
* HIGH.

Nivo aktivnosti može biti direktno određen aktivnim simulacionim scenarijem ili izveden iz podataka o koracima i kretanju.

9.5. Simulacija baterije

Naziv:

BatterySensor ili BatteryModel

Vrijednosti:

* batteryPercentage;
* charging;
* estimatedRemainingTimeMinutes, opciono.

Baterija će se postepeno trošiti.

Brzina trošenja može zavisiti od:

* učestalosti očitavanja;
* učestalosti MQTT slanja;
* nivoa aktivnosti;
* statusa veze;
* OTA procesa.

Mora postojati mogućnost simuliranog punjenja.

9.6. Status senzora

Svaki senzor mora imati tehničko stanje.

Moguća stanja:

* INITIALIZING;
* OK;
* CALIBRATING;
* DEGRADED;
* FAILED;
* DISABLED.

Status senzora predstavlja tehničko stanje senzora, a ne zdravstveno stanje korisnika.

======================================================================
10. NOVA FUNKCIONALNOST U VERZIJI 2.0
=====================================

Nova softverska verzija biće:

2.0.0

Glavna svrha OTA demonstracije je prelazak sa verzije 1.0.0 na verziju 2.0.0.

Verzija 2.0.0 dodajeće:

1. podršku za simulirani SpO2 senzor;
2. novu SpO2 analitiku;
3. nove konfiguracione parametre;
4. novi prikaz u web aplikaciji;
5. novu sposobnost navedenu u listi capabilities uređaja.

Naziv novog senzora:

SpO2Sensor

Vrijednost:

oxygenSaturationPercentage

U simulaciji se pretpostavlja da uređaj ima simulirani hardverski profil koji može podržati ovaj senzor, ali verzija 1.0.0 nema odgovarajući softverski drajver i analitički modul.

OTA verzija 2.0.0 instalira:

* drajver simuliranog senzora;
* logiku generisanja SpO2 vrijednosti;
* validaciju podataka;
* SpO2 agregaciju;
* nove konfiguracione pragove;
* novu frontend karticu;
* novi istorijski grafikon.

Na ovaj način OTA dodaje stvarnu novu funkcionalnost, a ne samo novi broj verzije.

Nakon uspješnog OTA procesa Device Shadow treba prijaviti:

"softwareVersion": "2.0.0"

i listu sposobnosti koja sada uključuje:

"SPO2_MONITORING"

Web aplikacija nakon toga automatski prikazuje novu SpO2 karticu i novi grafikon.

Detekcija pada pomoću simuliranog akcelerometra može ostati opciono buduće proširenje. Ne predstavlja obavezni dio verzije 2.0.0.

======================================================================
11. SIMULACIONI SCENARIJI
=========================

Senzorske vrijednosti ne smiju biti samo nepovezani slučajni brojevi.

Mora postojati ScenarioEngine koji definiše kontekst simulacije.

Obavezni scenariji:

1. SLEEPING

Simulira korisnika koji spava.

Karakteristike:

* nema koraka;
* nizak nivo aktivnosti;
* puls se postepeno stabilizuje;
* temperatura se sporo mijenja;
* baterija se normalno troši.

2. RESTING

Simulira budnog korisnika koji miruje.

Karakteristike:

* veoma malo ili nimalo koraka;
* stabilna srčana frekvencija;
* stabilna temperatura;
* nivo aktivnosti RESTING.

3. WALKING

Simulira hodanje.

Karakteristike:

* broj koraka raste;
* puls postepeno raste;
* nivo aktivnosti postaje LIGHT ili MODERATE;
* baterija se nešto brže troši.

4. RUNNING

Simulira trčanje.

Karakteristike:

* koraci brzo rastu;
* puls postepeno dostiže višu ciljnu vrijednost;
* nivo aktivnosti je HIGH;
* baterija se troši brže.

5. EXERCISING

Simulira drugu vrstu treninga.

Karakteristike:

* puls raste;
* koraci mogu rasti sporije nego tokom trčanja;
* nivo aktivnosti je HIGH.

6. RECOVERY

Simulira period nakon aktivnosti.

Karakteristike:

* puls se postepeno vraća prema vrijednosti mirovanja;
* broj koraka opada;
* aktivnost prelazi iz HIGH u MODERATE ili RESTING.

7. STRESS_EVENT

Simulacioni test u kojem puls raste iako korisnik miruje.

Koristi se za provjeru:

* lokalne analitike;
* upozorenja;
* korelacije pulsa i aktivnosti;
* slanja alert poruke.

Ovaj scenario nema medicinsko značenje. Služi samo kao tehnički test.

8. SENSOR_FAILURE

Simulira kvar odabranog senzora.

9. LOW_BATTERY

Simulira brzo pražnjenje ili unaprijed postavlja nizak nivo baterije.

10. NETWORK_OUTAGE

Simulira prekid internet ili MQTT veze.

ScenarioEngine mora podržavati ručno mijenjanje scenarija putem komande iz web aplikacije.

======================================================================
12. REALISTIČNO GENERISANJE PODATAKA
====================================

Podaci moraju djelovati povezano i uvjerljivo.

Ne treba raditi:

heartRate = random broj između 40 i 180 pri svakom očitavanju.

Umjesto toga, svaki senzor treba da ima:

* trenutnu vrijednost;
* ciljnu vrijednost;
* maksimalnu brzinu promjene;
* dozvoljeni slučajni šum;
* opcioni drift;
* status senzora.

Primjer promjene pulsa pri prelasku sa mirovanja na trčanje:

72, 76, 81, 88, 96, 105, 116, 128...

Umjesto:

72, 150, 61, 173, 90...

Simulacioni scenario određuje ciljnu oblast, ali senzor postepeno mijenja vrijednost.

Senzori treba da budu međusobno povezani.

Primjeri:

* kada raste nivo aktivnosti, raste broj koraka;
* kada korisnik trči, puls postepeno raste;
* nakon trčanja puls postepeno opada;
* češća mjerenja i slanja povećavaju potrošnju baterije;
* tokom prekida mreže raste broj lokalno sačuvanih poruka.

Mora postojati podrška za determinističko testiranje pomoću postavljanja random seed vrijednosti.

======================================================================
13. STANJA UREĐAJA
==================

Uređaj mora znati u kojem se stanju nalazi.

Biće implementiran kao konačni automat, odnosno state machine.

Predložena stanja:

1. BOOTING

Aplikacija se pokreće i učitava lokalnu konfiguraciju.

2. SELF_TEST

Provjeravaju se:

* dostupnost modula;
* lokalna baza;
* sertifikati;
* stanje senzora;
* integritet osnovne konfiguracije.

3. CONNECTING

Uređaj pokušava da se poveže sa AWS IoT Core.

4. MONITORING

Normalno očitavanje senzora, analitika i slanje podataka.

5. WARNING

Postoji aktivno upozorenje, ali uređaj može nastaviti rad.

6. DEGRADED

Jedan senzor ili dio sistema ne radi pravilno, ali preostale funkcionalnosti nastavljaju rad.

7. OFFLINE

Uređaj nije povezan sa AWS-om, ali nastavlja lokalno očitavanje i analitiku.

8. LOW_BATTERY

Baterija je ispod konfigurisanog praga.

9. CHARGING

Simulira se punjenje baterije.

10. MAINTENANCE

Uređaj je u servisnom režimu.

U ovom režimu može:

* zaustaviti normalno mjerenje;
* primati servisne komande;
* kalibrisati senzore;
* izvršavati dijagnostiku.

11. UPDATING

U toku je OTA nadogradnja.

12. RESTARTING

Aplikacija se priprema za restart.

13. ERROR

Postoji ozbiljna greška koja sprečava normalan rad.

14. SHUTTING_DOWN

Uređaj se kontrolisano zaustavlja.

Svaka promjena stanja mora biti evidentirana i po mogućnosti poslata kao event poruka.

======================================================================
14. MODULARNA ARHITEKTURA SIMULIRANOG UREĐAJA
=============================================

Simulator ne smije biti implementiran kao jedan veliki Python fajl.

Predložena struktura:

wearable-iot-thesis/
|
|-- device_simulator/
|   |
|   |-- main.py
|   |-- application.py
|   |
|   |-- core/
|   |   |-- device_controller.py
|   |   |-- device_state.py
|   |   |-- state_machine.py
|   |   |-- event_bus.py
|   |   |-- scheduler.py
|   |
|   |-- sensors/
|   |   |-- base_sensor.py
|   |   |-- heart_rate_sensor.py
|   |   |-- skin_temperature_sensor.py
|   |   |-- step_counter_sensor.py
|   |   |-- battery_model.py
|   |   |-- spo2_sensor.py
|   |   |-- sensor_manager.py
|   |
|   |-- simulation/
|   |   |-- scenario.py
|   |   |-- scenario_engine.py
|   |   |-- signal_generator.py
|   |   |-- user_profile.py
|   |
|   |-- analytics/
|   |   |-- base_analyzer.py
|   |   |-- rolling_statistics.py
|   |   |-- health_metrics_analyzer.py
|   |   |-- activity_analyzer.py
|   |   |-- spo2_analyzer.py
|   |   |-- analytics_manager.py
|   |
|   |-- alerts/
|   |   |-- alert.py
|   |   |-- alert_manager.py
|   |   |-- threshold_evaluator.py
|   |
|   |-- communication/
|   |   |-- mqtt_client.py
|   |   |-- mqtt_topics.py
|   |   |-- message_serializer.py
|   |   |-- shadow_client.py
|   |   |-- connection_manager.py
|   |
|   |-- commands/
|   |   |-- command.py
|   |   |-- command_handler.py
|   |   |-- command_validator.py
|   |   |-- command_registry.py
|   |
|   |-- configuration/
|   |   |-- device_config.py
|   |   |-- configuration_manager.py
|   |   |-- configuration_validator.py
|   |   |-- default_config.json
|   |
|   |-- device_health/
|   |   |-- device_health_monitor.py
|   |   |-- sensor_health_monitor.py
|   |   |-- resource_monitor.py
|   |   |-- fault_manager.py
|   |
|   |-- storage/
|   |   |-- local_database.py
|   |   |-- offline_queue.py
|   |   |-- synchronization_manager.py
|   |
|   |-- ota/
|   |   |-- ota_agent.py
|   |   |-- job_handler.py
|   |   |-- package_downloader.py
|   |   |-- package_verifier.py
|   |   |-- release_manager.py
|   |   |-- rollback_manager.py
|   |
|   |-- models/
|   |   |-- telemetry.py
|   |   |-- analytics_result.py
|   |   |-- device_health.py
|   |   |-- event.py
|   |   |-- alert.py
|   |
|   |-- utils/
|       |-- time_utils.py
|       |-- id_utils.py
|       |-- logging_config.py
|
|-- control_backend/
|   |
|   |-- main.py
|   |-- settings.py
|   |
|   |-- api/
|   |   |-- device_routes.py
|   |   |-- configuration_routes.py
|   |   |-- command_routes.py
|   |   |-- history_routes.py
|   |   |-- ota_routes.py
|   |
|   |-- aws/
|   |   |-- iot_data_client.py
|   |   |-- mqtt_subscriber.py
|   |   |-- shadow_service.py
|   |   |-- dynamodb_service.py
|   |   |-- jobs_service.py
|   |   |-- s3_service.py
|   |
|   |-- websocket/
|   |   |-- connection_manager.py
|   |   |-- event_broadcaster.py
|   |
|   |-- models/
|   |-- services/
|
|-- web_frontend/
|   |
|   |-- index.html
|   |-- pages/
|   |-- css/
|   |   |-- variables.css
|   |   |-- layout.css
|   |   |-- components.css
|   |   |-- animations.css
|   |
|   |-- js/
|   |   |-- api.js
|   |   |-- websocket.js
|   |   |-- dashboard.js
|   |   |-- simulation.js
|   |   |-- charts.js
|   |   |-- configuration.js
|   |   |-- commands.js
|   |   |-- ota.js
|   |
|   |-- assets/
|       |-- svg/
|       |-- icons/
|
|-- infrastructure/
|   |-- iot_policies/
|   |-- iot_rules/
|   |-- job_documents/
|   |-- dynamodb/
|
|-- ota_artifacts/
|   |-- version_1.0.0/
|   |-- version_2.0.0/
|
|-- scripts/
|   |-- create_history_data.py
|   |-- build_release.py
|   |-- calculate_sha256.py
|   |-- upload_release.py
|
|-- tests/
|   |-- unit/
|   |-- integration/
|   |-- end_to_end/
|
|-- docs/
|-- requirements.txt
|-- .env.example
|-- .gitignore
|-- README.md

======================================================================
15. ODGOVORNOSTI GLAVNIH MODULA
===============================

15.1. DeviceController

Centralno koordinira uređaj.

Odgovoran je za:

* pokretanje uređaja;
* prelazak između stanja;
* pokretanje senzora;
* pokretanje analitike;
* obradu događaja;
* kontrolisano gašenje;
* koordinaciju OTA procesa.

Ne treba direktno implementirati detalje MQTT-a, senzora ili baze.

15.2. StateMachine

Čuva trenutno stanje uređaja.

Provjerava da li je prelazak između stanja dozvoljen.

Primjer:

MONITORING -> UPDATING je dozvoljeno.

ERROR -> MONITORING nije dozvoljeno bez oporavka ili restarta.

15.3. SensorManager

Registruje i upravlja senzorima.

Omogućava:

* čitanje svih aktivnih senzora;
* uključivanje i isključivanje senzora;
* provjeru statusa;
* kalibraciju;
* dodavanje novog senzora nakon OTA nadogradnje.

15.4. ScenarioEngine

Određuje aktivni simulacioni scenario.

Šalje senzorima kontekst potreban za generisanje povezanih vrijednosti.

15.5. AnalyticsManager

Prima mjerenja i čuva ih u memorijskom prozoru.

Periodično računa agregirane rezultate.

15.6. AlertManager

Provjerava:

* prekoračenje pragova;
* kvarove senzora;
* nedostatak podataka;
* nizak nivo baterije;
* dug prekid veze;
* neuspješnu OTA nadogradnju.

Sprječava prečesto ponavljanje istog upozorenja.

15.7. MqttClient

Sadrži samo MQTT komunikacionu logiku.

Odgovoran je za:

* povezivanje;
* reconnect;
* subscribe;
* publish;
* QoS;
* obradu primljenih poruka;
* prijavu grešaka.

15.8. ShadowClient

Obrađuje Device Shadow komunikaciju.

Odgovoran je za:

* preuzimanje Shadow dokumenta;
* primanje delta promjena;
* slanje reported stanja;
* prijavu odbijene konfiguracije.

15.9. CommandHandler

Prima validirane komande i prosljeđuje ih odgovarajućem modulu.

15.10. DeviceHealthMonitor

Prati tehničko stanje uređaja.

15.11. OfflineQueue

Čuva poruke koje nisu uspješno poslate.

15.12. OtaAgent

Izvršava kompletan OTA tok.

======================================================================
16. DALJINSKA KONFIGURACIJA
===========================

Daljinska konfiguracija vršiće se preko AWS IoT Device Shadow mehanizma.

Korisnička aplikacija mijenja desired dio Shadow dokumenta.

Uređaj prima delta poruku.

Uređaj zatim:

1. parsira konfiguraciju;
2. validira sve vrijednosti;
3. odbija nevažeće vrijednosti;
4. primjenjuje validnu konfiguraciju;
5. čuva je lokalno;
6. šalje applied vrijednosti u reported dio;
7. generiše događaj o promjeni konfiguracije.

Konfiguracioni parametri:

* measurementIntervalSec;
* telemetryIntervalSec;
* analyticsWindowSec;
* healthReportIntervalSec;
* temperatureUnit;
* heartRateMinimumThreshold;
* heartRateMaximumRestingThreshold;
* skinTemperatureMinimumThreshold;
* skinTemperatureMaximumThreshold;
* lowBatteryThresholdPercentage;
* alertsEnabled;
* heartRateAlertsEnabled;
* temperatureAlertsEnabled;
* batteryAlertsEnabled;
* sensorFailureAlertsEnabled;
* offlineQueueMaximumItems;
* activeUserProfile;
* analyticsEnabled.

Nakon verzije 2.0.0 dodaju se:

* spo2AlertsEnabled;
* spo2MinimumThreshold;
* spo2MeasurementEnabled.

Primjer Shadow desired dokumenta:

{
"state": {
"desired": {
"measurementIntervalSec": 2,
"telemetryIntervalSec": 10,
"analyticsWindowSec": 60,
"healthReportIntervalSec": 30,
"temperatureUnit": "CELSIUS",
"thresholds": {
"heartRateMinimumBpm": 50,
"heartRateMaximumRestingBpm": 110,
"skinTemperatureMinimumC": 30.0,
"skinTemperatureMaximumC": 37.0,
"lowBatteryPercentage": 15
},
"alerts": {
"enabled": true,
"heartRate": true,
"temperature": true,
"battery": true,
"sensorFailure": true
}
}
}
}

Navedene vrijednosti služe kao demonstraciona konfiguracija, a ne kao medicinske preporuke.

Primjeri nevažeće konfiguracije:

* negativan period očitavanja;
* period očitavanja jednak nuli;
* nepoznata temperaturna jedinica;
* donji prag veći od gornjeg;
* procenat baterije manji od 0 ili veći od 100;
* period telemetrije manji od dozvoljenog minimuma;
* SpO2 konfiguracija poslata uređaju verzije 1.0.0.

Uređaj ne smije srušiti aplikaciju zbog loše konfiguracije.

======================================================================
17. KOMANDE
===========

Konfiguracija i komande predstavljaju različite pojmove.

Konfiguracija:

* mijenja trajne postavke;
* čuva se kroz Device Shadow.

Komanda:

* predstavlja jednokratnu akciju;
* šalje se preko MQTT topic-a;
* ima commandId;
* uređaj vraća rezultat izvršenja.

Obavezne komande:

* START_MONITORING;
* STOP_MONITORING;
* RESTART_DEVICE;
* ENTER_MAINTENANCE;
* EXIT_MAINTENANCE;
* START_CHARGING;
* STOP_CHARGING;
* CALIBRATE_SENSOR;
* REQUEST_IMMEDIATE_MEASUREMENT;
* REQUEST_DEVICE_HEALTH;
* CLEAR_ALERTS;
* CHANGE_SIMULATION_SCENARIO;
* SIMULATE_SENSOR_FAILURE;
* RESTORE_SENSOR;
* SIMULATE_NETWORK_OUTAGE;
* RESTORE_NETWORK.

Primjer komande:

{
"schemaVersion": 1,
"commandId": "cmd-205",
"deviceId": "healthband-device-001",
"type": "CHANGE_SIMULATION_SCENARIO",
"parameters": {
"scenario": "RUNNING"
},
"timestamp": "2026-07-15T14:20:00Z"
}

Primjer odgovora:

{
"schemaVersion": 1,
"commandId": "cmd-205",
"deviceId": "healthband-device-001",
"status": "SUCCEEDED",
"message": "Simulation scenario changed to RUNNING.",
"timestamp": "2026-07-15T14:20:01Z"
}

Mogući statusi:

* RECEIVED;
* IN_PROGRESS;
* SUCCEEDED;
* FAILED;
* REJECTED.

Uređaj mora čuvati nedavno obrađene commandId vrijednosti.

Ako zbog QoS 1 komunikacije ponovo primi istu komandu, ne treba je izvršiti dva puta. Treba vratiti prethodni rezultat ili označiti komandu kao već obrađenu.

======================================================================
18. LOKALNA ANALITIKA
=====================

Lokalna analitika je obavezna.

Analitika se izvršava unutar simulatora uređaja prije slanja agregiranih rezultata u cloud.

Osnovna implementacija neće zavisiti od Greengrass-a.

Za svako mjerenje AnalyticsManager dodaje podatak u odgovarajući vremenski prozor.

Konfiguracioni parametar:

analyticsWindowSec

Primjer:

60 sekundi.

Na kraju prozora računaju se:

Za srčanu frekvenciju:

* prosječna vrijednost;
* minimalna vrijednost;
* maksimalna vrijednost;
* broj validnih mjerenja;
* broj odbačenih mjerenja;
* broj prekoračenja praga.

Za temperaturu:

* prosječna vrijednost;
* minimalna vrijednost;
* maksimalna vrijednost;
* broj validnih mjerenja.

Za korake:

* ukupan broj koraka u prozoru;
* prosječan broj koraka po podintervalu;
* procijenjeni nivo aktivnosti.

Za bateriju:

* početni procenat;
* završni procenat;
* potrošnja tokom prozora.

Dodatno:

* dominantni scenario;
* dominantni nivo aktivnosti;
* broj generisanih upozorenja;
* procenat validnih senzorskih podataka.

Nakon verzije 2.0.0 za SpO2 se računaju:

* prosječna vrijednost;
* minimalna vrijednost;
* maksimalna vrijednost;
* broj mjerenja ispod konfigurisanog praga;
* kvalitet podataka.

Primjer agregirane poruke:

{
"schemaVersion": 1,
"messageId": "uuid",
"deviceId": "healthband-device-001",
"windowStart": "2026-07-15T14:00:00Z",
"windowEnd": "2026-07-15T14:01:00Z",
"softwareVersion": "1.0.0",
"analytics": {
"heartRate": {
"averageBpm": 87.4,
"minimumBpm": 72,
"maximumBpm": 118,
"validSamples": 30
},
"skinTemperature": {
"averageCelsius": 33.8,
"minimumCelsius": 33.5,
"maximumCelsius": 34.1
},
"steps": {
"total": 84
},
"activity": {
"dominantLevel": "MODERATE"
},
"alertsGenerated": 0,
"dataQualityPercentage": 100
}
}

======================================================================
19. UPOZORENJA
==============

AlertManager generiše upozorenja na osnovu konfigurisanih pravila.

Obavezne vrste upozorenja:

* HEART_RATE_BELOW_THRESHOLD;
* HEART_RATE_ABOVE_RESTING_THRESHOLD;
* TEMPERATURE_BELOW_THRESHOLD;
* TEMPERATURE_ABOVE_THRESHOLD;
* LOW_BATTERY;
* SENSOR_NO_DATA;
* SENSOR_INVALID_VALUE;
* SENSOR_FAILED;
* MQTT_DISCONNECTED;
* OFFLINE_QUEUE_NEAR_LIMIT;
* OTA_UPDATE_FAILED;
* DEVICE_INTERNAL_ERROR.

Nakon verzije 2.0.0:

* SPO2_BELOW_THRESHOLD;
* SPO2_SENSOR_FAILED.

Nivoi ozbiljnosti:

* INFO;
* WARNING;
* HIGH.

Nazivi predstavljaju tehničke nivoe prioriteta, a ne medicinsku dijagnozu.

Da bi se izbjeglo generisanje upozorenja pri jednom kratkom odstupanju, koristiće se:

* broj uzastopnih prekoračenja;
* minimalno trajanje stanja;
* cooldown period;
* opcionalna histereza.

Primjer:

Upozorenje se generiše tek nakon tri uzastopna mjerenja izvan konfigurisanog opsega.

Primjer alert poruke:

{
"schemaVersion": 1,
"alertId": "alert-1042",
"deviceId": "healthband-device-001",
"type": "HEART_RATE_ABOVE_RESTING_THRESHOLD",
"severity": "WARNING",
"measuredValue": 128,
"configuredThreshold": 110,
"activityLevel": "RESTING",
"scenario": "STRESS_EVENT",
"timestamp": "2026-07-15T14:12:04Z",
"simulated": true
}

======================================================================
20. MONITORING ZDRAVLJA SAMOG UREĐAJA
=====================================

Mora se jasno razlikovati:

1. zdravstveni i aktivnosti parametri simuliranog korisnika;
2. tehničko zdravlje HealthBand uređaja.

DeviceHealthMonitor pratiće:

* trenutno stanje uređaja;
* verziju softvera;
* vrijeme neprekidnog rada;
* status MQTT veze;
* vrijeme posljednje uspješne komunikacije;
* broj pokušaja ponovnog povezivanja;
* broj neuspješnih slanja;
* broj stavki u offline redu;
* veličinu lokalne baze;
* nivo baterije;
* status punjenja;
* status svakog senzora;
* posljednju internu grešku;
* dostupnu memoriju;
* CPU opterećenje simulatora;
* stanje OTA modula;
* posljednji uspješni OTA update;
* podržane capabilities funkcionalnosti.

Moguća ukupna stanja zdravlja:

* HEALTHY;
* DEGRADED;
* UNHEALTHY.

Primjer health poruke:

{
"schemaVersion": 1,
"deviceId": "healthband-device-001",
"deviceStatus": "DEGRADED",
"deviceState": "MONITORING",
"softwareVersion": "1.0.0",
"uptimeSec": 28400,
"mqttConnected": true,
"batteryPercentage": 42,
"offlineQueueSize": 0,
"sensors": {
"heartRate": "OK",
"skinTemperature": "FAILED",
"stepCounter": "OK",
"battery": "OK"
},
"capabilities": [
"HEART_RATE_MONITORING",
"SKIN_TEMPERATURE_MONITORING",
"STEP_COUNTING",
"LOCAL_ANALYTICS"
],
"lastError": "SKIN_TEMPERATURE_SENSOR_NO_DATA",
"timestamp": "2026-07-15T14:30:00Z"
}

======================================================================
21. RAD BEZ INTERNET VEZE
=========================

Uređaj mora nastaviti osnovni rad kada izgubi vezu sa AWS IoT Core.

Tokom prekida veze:

* senzori nastavljaju očitavanje;
* ScenarioEngine nastavlja rad;
* lokalna analitika nastavlja rad;
* upozorenja se i dalje generišu;
* poruke se čuvaju u SQLite bazi;
* uređaj prelazi u OFFLINE stanje;
* periodično pokušava ponovno povezivanje.

OfflineQueue mora čuvati najmanje:

* originalni timestamp;
* messageId;
* tip poruke;
* MQTT topic;
* payload;
* QoS;
* broj pokušaja slanja;
* status poruke.

Nakon ponovnog povezivanja:

1. uređaj ne prekida trenutna mjerenja;
2. pokreće se sinhronizacija;
3. prvo se šalju važna upozorenja i događaji;
4. zatim agregirani podaci;
5. nakon toga telemetrija;
6. uspješno poslate stavke uklanjaju se iz offline reda.

Svaka poruka ima jedinstveni messageId kako bi backend ili baza mogli prepoznati eventualni duplikat.

Ako offline red dostigne maksimalnu veličinu, prioritet imaju:

1. upozorenja;
2. događaji;
3. agregirani podaci;
4. health poruke;
5. sirova telemetrija.

Najstarija nevažna telemetrija može biti odbačena ako je red pun.

======================================================================
22. MQTT TOPIC STRUKTURA
========================

Koristiće se sljedeći vlastiti MQTT topic-i:

healthband/{deviceId}/telemetry

Namjena:
Trenutna senzorska očitavanja.

healthband/{deviceId}/analytics

Namjena:
Lokalno izračunati agregirani podaci.

healthband/{deviceId}/alerts

Namjena:
Upozorenja.

healthband/{deviceId}/health

Namjena:
Tehničko stanje uređaja.

healthband/{deviceId}/events

Namjena:
Promjene stanja, povezivanje, restart, konfiguracija i OTA događaji.

healthband/{deviceId}/commands/request

Namjena:
Komande koje korisnička aplikacija šalje uređaju.

healthband/{deviceId}/commands/response

Namjena:
Rezultati izvršenja komandi.

healthband/{deviceId}/presence

Namjena:
Online/offline status ili heartbeat.

Device Shadow koristiće AWS rezervisane topic-e za odgovarajući Thing.

Primjeri:

$aws/things/{thingName}/shadow/get

$aws/things/{thingName}/shadow/update

$aws/things/{thingName}/shadow/update/delta

$aws/things/{thingName}/shadow/update/accepted

AWS IoT Jobs koristiće rezervisane job topic-e.

Primjeri:

$aws/things/{thingName}/jobs/notify-next

$aws/things/{thingName}/jobs/$next/get

$aws/things/{thingName}/jobs/{jobId}/update

Za reserved topic-e prvenstveno treba koristiti AWS IoT Device SDK umjesto ručnog formiranja svih poruka.

======================================================================
23. MQTT QoS PRAVILA
====================

Predložena pravila:

Telemetrija:

QoS 0 tokom normalnog rada, jer se brzo generiše i gubitak jednog uzorka nije kritičan.

Agregirana analitika:

QoS 1.

Upozorenja:

QoS 1.

Health poruke:

QoS 1.

Događaji:

QoS 1.

Komande:

QoS 1.

Odgovori na komande:

QoS 1.

OTA Jobs:

Prema zahtjevima AWS IoT Jobs SDK-a.

Zbog mogućnosti duplikata kod QoS 1 poruka, poruke moraju imati jedinstvene identifikatore i obrada mora biti idempotentna.

======================================================================
24. FORMAT TELEMETRIJSKE PORUKE
===============================

Primjer telemetrije verzije 1.0.0:

{
"schemaVersion": 1,
"messageId": "uuid",
"deviceId": "healthband-device-001",
"userId": "simulated-user-001",
"timestamp": "2026-07-15T14:30:00Z",
"softwareVersion": "1.0.0",
"deviceState": "MONITORING",
"scenario": "WALKING",
"measurements": {
"heartRateBpm": 92,
"skinTemperature": 33.8,
"temperatureUnit": "CELSIUS",
"stepsInInterval": 18,
"totalDailySteps": 4210,
"activityLevel": "MODERATE",
"batteryPercentage": 76
},
"sensorStatus": {
"heartRate": "OK",
"skinTemperature": "OK",
"stepCounter": "OK",
"battery": "OK"
},
"simulated": true
}

Primjer telemetrije verzije 2.0.0:

{
"schemaVersion": 2,
"messageId": "uuid",
"deviceId": "healthband-device-001",
"userId": "simulated-user-001",
"timestamp": "2026-07-15T14:30:00Z",
"softwareVersion": "2.0.0",
"deviceState": "MONITORING",
"scenario": "RESTING",
"measurements": {
"heartRateBpm": 74,
"skinTemperature": 33.6,
"temperatureUnit": "CELSIUS",
"stepsInInterval": 0,
"totalDailySteps": 4210,
"activityLevel": "RESTING",
"batteryPercentage": 74,
"oxygenSaturationPercentage": 98
},
"sensorStatus": {
"heartRate": "OK",
"skinTemperature": "OK",
"stepCounter": "OK",
"battery": "OK",
"spo2": "OK"
},
"simulated": true
}

Svi timestamp podaci moraju biti u UTC vremenu i ISO 8601 formatu.

======================================================================
25. AWS RESURSI
===============

25.1. AWS IoT Thing

Naziv:

healthband-device-001

Thing predstavlja simulirani uređaj.

25.2. Sertifikat uređaja

Uređaj dobija:

* X.509 sertifikat;
* privatni ključ;
* Amazon Root CA sertifikat.

Privatni ključ ne smije biti postavljen u Git repozitorijum.

25.3. IoT Policy uređaja

Policy treba koristiti princip najmanjih privilegija.

Uređaj smije:

* povezati se kao svoj clientId;
* objavljivati samo na svojim topic-ima;
* primati samo svoje komande;
* pristupati samo svom Shadow-u;
* pristupati samo svojim Jobs topic-ima.

Ne treba koristiti široku policy dozvolu sa Resource: "*" osim privremeno tokom prvog testa, a i tada je treba kasnije ukloniti.

25.4. Poseban identitet za web backend

Web backend ne smije koristiti sertifikat i privatni ključ uređaja.

Backend treba imati:

* zaseban aplikacioni sertifikat za MQTT subscription, ili drugi odgovarajući AWS identitet;
* IAM profil ili rolu za boto3 operacije;
* ograničene dozvole.

Browser ne smije direktno dobijati:

* AWS access key;
* secret access key;
* privatni X.509 ključ;
* administratorske AWS dozvole.

25.5. DynamoDB tabele

Predložene tabele:

HealthBandTelemetry

Partition key:
deviceId

Sort key:
timestamp

Namjena:
Sirova ili periodična telemetrija.

HealthBandAnalytics

Partition key:
deviceId

Sort key:
windowEnd

Namjena:
Agregirani podaci za istorijske grafikone.

HealthBandEvents

Partition key:
deviceId

Sort key:
timestampEventId

Namjena:

* upozorenja;
* promjene stanja;
* izvršene komande;
* OTA događaji;
* kvarovi.

U svim tabelama može se dodati messageId radi deduplikacije.

25.6. IoT Rules

Predložena pravila:

StoreTelemetryRule

Sluša:

healthband/+/telemetry

Upisuje u:

HealthBandTelemetry

StoreAnalyticsRule

Sluša:

healthband/+/analytics

Upisuje u:

HealthBandAnalytics

StoreAlertsRule

Sluša:

healthband/+/alerts

Upisuje u:

HealthBandEvents

StoreEventsRule

Sluša:

healthband/+/events

Upisuje u:

HealthBandEvents

DeviceLogsRule, opciono

Sluša log topic i šalje podatke u CloudWatch Logs.

25.7. S3 bucket

Primjer naziva:

healthband-ota-artifacts-<unique-suffix>

Bucket mora biti:

* privatan;
* bez javnog pristupa;
* sa uključenim versioningom ako je dostupno;
* dostupan IoT Jobs servisu preko odgovarajuće IAM role.

25.8. CloudWatch

CloudWatch će se koristiti za:

* AWS IoT logove;
* provjeru MQTT grešaka;
* provjeru IoT Rules grešaka;
* pregled neuspješnih autorizacija;
* OTA dijagnostiku.

======================================================================
26. ISTORIJSKI PODACI I PRIKAZ POSLJEDNJIH 30 DANA
==================================================

Aplikacija mora imati mogućnost izbora perioda:

* posljednjih 15 minuta;
* posljednji sat;
* posljednja 24 sata;
* posljednjih 7 dana;
* posljednjih 30 dana;
* proizvoljan vremenski interval, opciono.

Za kratke periode mogu se prikazivati detaljnija telemetrijska mjerenja.

Za duže periode treba koristiti agregirane podatke kako grafikon ne bi sadržao previše tačaka.

Predložena politika:

* sirova telemetrija čuva se kraće, na primjer 7 dana;
* agregirani podaci čuvaju se najmanje 30 ili 90 dana;
* upozorenja i događaji čuvaju se najmanje 90 dana.

Za demonstraciju istorije nije potrebno čekati da projekat radi mjesec dana.

Biće napravljen skript:

scripts/create_history_data.py

Skript će:

* generisati sintetičke agregirane podatke za prethodnih 30 dana;
* koristiti iste modele scenarija kao simulator;
* dodijeliti odgovarajuće timestamp vrijednosti;
* upisati podatke u DynamoDB;
* jasno označiti podatke kao simulirane.

Time će istorijski prikaz moći biti demonstriran odmah.

======================================================================
27. WEB BACKEND REST API
========================

Predloženi endpoint-i:

GET /api/devices

Vraća listu dostupnih uređaja.

GET /api/devices/{deviceId}

Vraća osnovne informacije o uređaju.

GET /api/devices/{deviceId}/state

Vraća trenutno stanje.

GET /api/devices/{deviceId}/health

Vraća posljednji health izvještaj.

GET /api/devices/{deviceId}/configuration

Vraća trenutno desired i reported stanje konfiguracije.

PUT /api/devices/{deviceId}/configuration

Mijenja desired konfiguraciju u Device Shadow dokumentu.

POST /api/devices/{deviceId}/commands

Šalje komandu uređaju.

GET /api/devices/{deviceId}/commands/{commandId}

Vraća status komande.

GET /api/devices/{deviceId}/telemetry

Vraća telemetriju u izabranom periodu.

GET /api/devices/{deviceId}/analytics

Vraća agregirane podatke.

GET /api/devices/{deviceId}/alerts

Vraća upozorenja.

GET /api/devices/{deviceId}/events

Vraća događaje.

GET /api/devices/{deviceId}/ota

Vraća verziju i trenutno OTA stanje.

POST /api/devices/{deviceId}/ota

Pokreće IoT Job za odabranu verziju.

GET /api/releases

Vraća dostupne OTA pakete.

WebSocket endpoint:

/ws/devices/{deviceId}

Preko njega browser dobija:

* novu telemetriju;
* novu analitiku;
* upozorenja;
* health izvještaje;
* rezultate komandi;
* promjene OTA statusa.

======================================================================
28. WEB KORISNIČKI INTERFEJS
============================

Interfejs treba izgledati kao moderan IoT dashboard, a ne kao osnovna HTML stranica.

Glavni meni:

* Dashboard;
* Live Simulation;
* History;
* Configuration;
* Commands;
* Device Health;
* OTA Update;
* Event Log.

28.1. Dashboard

Prikazuje:

* naziv uređaja;
* online/offline status;
* trenutno stanje;
* softversku verziju;
* aktivni scenario;
* puls;
* temperaturu;
* korake;
* aktivnost;
* bateriju;
* posljednje upozorenje;
* stanje MQTT veze.

Nakon verzije 2.0.0 prikazuje i SpO2.

28.2. Live Simulation

Centralni dio predstavlja stilizovanu pametnu narukvicu.

Narukvica može biti nacrtana pomoću:

* HTML elemenata;
* CSS-a;
* SVG-a.

Na ekranu narukvice prikazuju se:

* animirano srce;
* trenutni puls;
* koraci;
* baterija;
* aktivnost;
* SpO2 nakon OTA nadogradnje.

Animacija srca treba pratiti puls.

Interval animacije približno se određuje formulom:

60000 / heartRateBpm

Ako je puls 60 BPM, srce se animira približno jednom u sekundi.

Ako je puls 120 BPM, animira se približno dva puta u sekundi.

Pored narukvice prikazuje se animacija ili ikona aktivnosti:

* spavanje;
* mirovanje;
* hodanje;
* trčanje;
* trening;
* oporavak.

Prilikom promjene scenarija prikaz se mijenja bez osvježavanja stranice.

28.3. Kartice senzora

Svaki senzor ima karticu koja prikazuje:

* naziv;
* vrijednost;
* jedinicu;
* status;
* vrijeme posljednjeg očitavanja;
* mali trend;
* upozorenje ako postoji.

Ako senzor ne radi:

* kartica prikazuje „NEMA PODATAKA“;
* prikazuje status FAILED;
* dobija vizuelno upozorenje.

28.4. History

Prikazuje grafikone:

* puls kroz vrijeme;
* temperatura kroz vrijeme;
* koraci;
* baterija;
* broj upozorenja;
* SpO2 nakon nadogradnje.

Omogućava izbor perioda.

28.5. Configuration

Sadrži formu za:

* period očitavanja;
* period telemetrije;
* period analitike;
* temperaturnu jedinicu;
* pragove;
* uključivanje upozorenja;
* maksimalnu veličinu offline reda.

Treba prikazati:

* desired vrijednost;
* reported vrijednost;
* status sinhronizacije.

Ako se desired i reported razlikuju, prikazuje se:

„Čeka se primjena konfiguracije.“

Ako uređaj odbije konfiguraciju, prikazuje se razlog.

28.6. Commands

Sadrži dugmad i forme za slanje komandi.

Za svaku poslatu komandu prikazuje:

* commandId;
* vrijeme slanja;
* status;
* rezultat;
* poruku greške.

28.7. Device Health

Prikazuje:

* ukupno tehničko stanje;
* MQTT status;
* uptime;
* CPU;
* memoriju;
* lokalnu bazu;
* offline red;
* bateriju;
* senzore;
* verziju;
* capabilities;
* posljednju grešku.

28.8. OTA Update

Prikazuje:

* trenutno instaliranu verziju;
* dostupne verzije;
* listu novih funkcionalnosti;
* dugme za pokretanje nadogradnje;
* status AWS IoT Job-a;
* progress bar;
* fazu instalacije;
* rezultat self-testa;
* rollback status.

Primjer faza:

* QUEUED;
* DOWNLOADING;
* VERIFYING;
* INSTALLING;
* RESTARTING;
* SELF_TEST;
* SUCCEEDED;
* FAILED;
* ROLLED_BACK.

28.9. Event Log

Prikazuje hronološku listu:

* pokretanja;
* povezivanja;
* prekida veze;
* promjena stanja;
* promjena konfiguracije;
* komandi;
* kvarova;
* upozorenja;
* OTA događaja.

======================================================================
29. TOK PODATAKA U REALNOM VREMENU
==================================

Tok telemetrije:

1. Senzor generiše mjerenje.
2. SensorManager formira skup mjerenja.
3. AnalyticsManager prima mjerenje.
4. AlertManager provjerava pravila.
5. MessageSerializer formira JSON poruku.
6. MqttClient objavljuje poruku na AWS IoT Core.
7. IoT Rule upisuje podatak u DynamoDB.
8. Posebna MQTT konekcija FastAPI backenda prima poruku.
9. FastAPI šalje podatak browseru preko WebSocket-a.
10. JavaScript ažurira brojeve, animacije i grafikone.

Tok konfiguracije:

1. Korisnik mijenja vrijednost u web aplikaciji.
2. Frontend šalje PUT zahtjev FastAPI backendu.
3. Backend validira osnovni format.
4. Backend ažurira desired dio Device Shadow dokumenta.
5. Uređaj prima Shadow delta.
6. Uređaj detaljno validira vrijednost.
7. Uređaj primjenjuje konfiguraciju.
8. Uređaj ažurira reported dio.
9. Backend i frontend prikazuju da je konfiguracija sinhronizovana.

Tok komande:

1. Frontend šalje POST zahtjev.
2. Backend generiše commandId.
3. Backend objavljuje MQTT poruku.
4. Uređaj prima komandu.
5. Uređaj potvrđuje prijem.
6. Uređaj izvršava komandu.
7. Uređaj objavljuje rezultat.
8. Backend dobija rezultat.
9. Frontend preko WebSocket-a prikazuje status.

Tok istorije:

1. Frontend traži period.
2. Backend formira DynamoDB query.
3. DynamoDB vraća podatke.
4. Backend ih sortira i po potrebi normalizuje.
5. Frontend prikazuje Chart.js grafikone.

======================================================================
30. OTA ARHITEKTURA
===================

OTA nadogradnja je jedan od najvažnijih dijelova projekta.

Pošto je uređaj simuliran na računaru, OTA predstavlja daljinsku nadogradnju Python aplikacije, a ne firmware fizičkog mikrokontrolera.

To mora biti jasno objašnjeno u diplomskom radu.

30.1. Struktura OTA paketa

Primjer paketa:

healthband-2.0.0.zip

Paket sadrži:

* nove Python module;
* manifest.json;
* informacije o verziji;
* listu capabilities;
* eventualne migracione skripte;
* self-test skriptu.

Primjer manifest dokumenta:

{
"product": "HealthBand",
"version": "2.0.0",
"minimumCurrentVersion": "1.0.0",
"artifact": "healthband-2.0.0.zip",
"sha256": "...",
"capabilities": [
"HEART_RATE_MONITORING",
"SKIN_TEMPERATURE_MONITORING",
"STEP_COUNTING",
"LOCAL_ANALYTICS",
"SPO2_MONITORING"
]
}

30.2. Job dokument

Job dokument treba sadržati najmanje:

* ciljnu verziju;
* URL ili S3 referencu paketa;
* SHA-256 hash;
* veličinu paketa;
* instrukciju tipa INSTALL_UPDATE;
* timeout;
* parametre restarta.

30.3. OTA tok

1. Verzija 2.0.0 se izgradi lokalno.
2. Izračuna se SHA-256 hash.
3. Paket se postavi u privatni S3 bucket.
4. Kreira se AWS IoT Job za healthband-device-001.
5. Uređaj prima job obavještenje.
6. Uređaj preuzima job dokument.
7. Uređaj provjerava da li je ciljna verzija novija.
8. Uređaj provjerava kompatibilnost.
9. Uređaj prelazi u UPDATING stanje.
10. Job status postaje IN_PROGRESS.
11. Uređaj preuzima paket preko vremenski ograničenog S3 URL-a.
12. Provjerava veličinu paketa.
13. Računa SHA-256.
14. Upoređuje hash sa manifestom.
15. Ako se hash ne podudara, instalacija se odbija.
16. Uređaj pravi rezervnu kopiju trenutne verzije.
17. Paket se raspakuje u privremeni release direktorijum.
18. Pokreće se pre-install provjera.
19. Aktivira se nova verzija.
20. Aplikacija se restartuje.
21. Nova verzija izvršava self-test.
22. Provjerava se da li je SpO2 modul dostupan.
23. Provjerava se da li MQTT veza radi.
24. Ako je sve uspješno, job dobija status SUCCEEDED.
25. Device Shadow prijavljuje verziju 2.0.0.
26. Frontend prikazuje novu SpO2 funkcionalnost.

30.4. Rollback

Ako nova verzija:

* ne može da se pokrene;
* ne prođe self-test;
* nema obavezne module;
* ne može da učita konfiguraciju;
* izaziva kritičnu grešku;

uređaj mora:

1. vratiti prethodnu verziju;
2. ponovo pokrenuti verziju 1.0.0;
3. prijaviti job status FAILED;
4. poslati OTA_UPDATE_FAILED događaj;
5. u health izvještaju navesti razlog rollback-a.

30.5. Organizacija verzija na disku

Preporučena struktura:

releases/
|-- 1.0.0/
|-- 2.0.0/

active_release.json

active_release.json sadrži trenutno aktivnu verziju.

Alternativno, na Linuxu se može koristiti simbolički link current.

30.6. Sigurnost OTA procesa

Obavezno:

* privatni S3 bucket;
* vremenski ograničen pristup paketu;
* SHA-256 provjera;
* validacija manifesta;
* provjera verzije;
* backup prethodne verzije;
* rollback;
* ograničena IAM rola.

Digitalni potpis paketa može se dodati kao napredno proširenje ako vrijeme dozvoli.

======================================================================
31. GREENGRASS
==============

AWS IoT Greengrass nije obavezan u prvoj implementaciji.

Obavezna lokalna analitika biće napravljena kao Python modul unutar simulatora.

Ako profesorica zatraži Greengrass ili ostane dovoljno vremena, AnalyticsManager se može prepakovati kao Greengrass komponenta.

U toj varijanti:

* računar sa simulatorom postaje Greengrass core uređaj;
* analitički modul se izvršava kao zasebna komponenta;
* senzorski modul šalje lokalne poruke;
* analitički modul lokalno obrađuje podatke;
* samo agregirani rezultat šalje se u AWS IoT Core.

Greengrass treba posmatrati kao opcionu fazu nakon završetka:

* osnovnog simulatora;
* AWS IoT Core povezivanja;
* Device Shadow konfiguracije;
* lokalne analitike;
* istorije;
* OTA mehanizma.

======================================================================
32. SIGURNOST
=============

Obavezne sigurnosne mjere:

1. MQTT preko TLS-a.

2. X.509 autentikacija uređaja.

3. Poseban sertifikat za svaki IoT klijent.

4. Poseban identitet uređaja i web backenda.

5. Princip najmanjih privilegija.

6. Privatni ključevi izvan Git repozitorijuma.

7. .gitignore mora isključivati:

* .env;
* certificates/;
* private keys;
* AWS credential fajlove;
* SQLite runtime baze;
* preuzete OTA pakete sa tajnim parametrima.

8. AWS ključevi ne smiju biti hardkodirani.

9. Browser ne smije dobijati AWS tajne podatke.

10. Komande moraju biti validirane.

11. Konfiguracija mora biti validirana.

12. Nepoznat tip komande mora biti odbijen.

13. Uređaj smije koristiti samo topic-e svog deviceId-a.

14. S3 OTA bucket mora biti privatan.

15. OTA paket mora proći provjeru integriteta.

16. Sistem koristi sintetičke podatke.

17. userId mora biti pseudonimizovan, na primjer:

simulated-user-001

18. Ne čuvaju se ime, prezime, JMBG, adresa ili stvarni zdravstveni podaci.

======================================================================
33. LOGGING
===========

Svaki važan modul treba koristiti Python logging.

Log mora sadržati:

* timestamp;
* nivo;
* naziv modula;
* poruku;
* correlationId ili commandId kada postoji;
* exception informacije kada dođe do greške.

Nivoi:

* DEBUG;
* INFO;
* WARNING;
* ERROR;
* CRITICAL.

Primjeri logova:

INFO Device entered MONITORING state.

INFO MQTT connection established.

WARNING Skin temperature sensor returned no data.

INFO Command cmd-205 received.

INFO OTA job job-2026-001 started.

ERROR OTA package hash verification failed.

Logovi ne smiju sadržati:

* privatne ključeve;
* AWS secret access key;
* kompletan sadržaj tajnih fajlova.

======================================================================
34. TESTIRANJE
==============

34.1. Unit testovi

Testirati:

* konverziju Celzijus/Farenhajt;
* konfiguracionu validaciju;
* generisanje senzorskih vrijednosti;
* state machine tranzicije;
* agregaciju;
* pragove upozorenja;
* command validation;
* deduplikaciju komandi;
* offline queue;
* SHA-256 provjeru;
* manifest validaciju;
* rollback logiku.

34.2. Integracioni testovi

Testirati:

* povezivanje sa AWS IoT Core;
* publish/subscribe;
* Device Shadow delta;
* Device Shadow reported update;
* IoT Rule upis u DynamoDB;
* FastAPI čitanje DynamoDB podataka;
* WebSocket ažuriranja;
* slanje komande preko backenda;
* povrat rezultata;
* AWS IoT Job tok.

34.3. End-to-end testovi

Testirati kompletne scenarije:

* normalan rad;
* promjena konfiguracije;
* promjena temperaturne jedinice;
* promjena aktivnosti;
* generisanje upozorenja;
* kvar senzora;
* gubitak veze;
* offline sinhronizacija;
* uspješan OTA;
* neuspješan OTA;
* rollback.

34.4. Test nevažeće konfiguracije

Uređaj mora odbiti nevažeću vrijednost bez rušenja.

34.5. Test QoS duplikata

Ista komanda sa istim commandId-om ne smije biti izvršena dva puta.

======================================================================
35. OBAVEZNI DEMONSTRACIONI SCENARIO
====================================

Na odbrani ili demonstraciji treba pokazati sljedeći tok:

1. Pokreće se HealthBand verzija 1.0.0.

2. Uređaj izvršava self-test.

3. Uređaj se pomoću X.509 sertifikata povezuje sa AWS IoT Core preko MQTT/TLS veze.

4. Web aplikacija prikazuje da je uređaj online.

5. Aktivira se RESTING scenario.

6. Na ekranu se vide puls, temperatura, koraci, aktivnost i baterija.

7. Podaci se uživo mijenjaju.

8. Web aplikacija prima podatke preko WebSocket-a.

9. Preko konfiguracije se period očitavanja promijeni, na primjer, sa pet na dvije sekunde.

10. Device Shadow šalje delta promjenu.

11. Uređaj validira i primjenjuje konfiguraciju.

12. Reported vrijednost potvrđuje primjenu.

13. Temperaturna jedinica mijenja se iz Celzijusa u Farenhajte.

14. Uređaj počinje prijavljivati temperaturu u novoj jedinici.

15. Šalje se komanda CHANGE_SIMULATION_SCENARIO sa vrijednošću RUNNING.

16. Puls i broj koraka postepeno rastu.

17. Lokalna analitika računa prosjek, minimum i maksimum.

18. Agregirani podatak se šalje u AWS.

19. Aktivira se STRESS_EVENT u stanju mirovanja.

20. Nakon potrebnog broja uzastopnih mjerenja generiše se upozorenje.

21. Upozorenje se prikazuje u web aplikaciji i čuva u DynamoDB.

22. Simulira se kvar temperaturnog senzora.

23. Kartica prikazuje „NEMA PODATAKA“.

24. Health status prelazi u DEGRADED.

25. Simulira se prekid mreže.

26. Uređaj prelazi u OFFLINE stanje.

27. Mjerenja se čuvaju u SQLite offline redu.

28. Veza se ponovo uspostavlja.

29. Zaostali podaci se sinhronizuju.

30. Prikazuje se istorija agregiranih podataka za prethodnih 30 dana.

31. Pokreće se OTA update sa 1.0.0 na 2.0.0.

32. AWS IoT Job prelazi u IN_PROGRESS.

33. Paket se preuzima sa privatnog S3 bucket-a.

34. Provjerava se SHA-256.

35. Instalira se nova verzija.

36. Uređaj se restartuje.

37. Self-test prolazi.

38. Job prelazi u SUCCEEDED.

39. Device Shadow prijavljuje verziju 2.0.0.

40. U capabilities listi pojavljuje se SPO2_MONITORING.

41. Na web interfejsu pojavljuje se nova SpO2 kartica.

42. Počinju stizati SpO2 mjerenja.

43. Prikazuje se SpO2 analitika.

44. Dodatno se može prikazati pokušaj instalacije oštećenog paketa i rollback.

======================================================================
36. KRITERIJUMI DA SE PROJEKAT SMATRA ZAVRŠENIM
===============================================

Projekat je završen kada su ispunjeni svi sljedeći kriterijumi:

* postoji modularni Python simulator wearable uređaja;
* uređaj ima jasno definisanu state machine logiku;
* postoje najmanje puls, temperatura, koraci, aktivnost i baterija;
* simulacioni scenariji daju povezane vrijednosti;
* uređaj se povezuje sa AWS IoT Core;
* koristi se MQTT preko TLS-a;
* koristi se X.509 sertifikat;
* uređaj šalje telemetriju;
* uređaj šalje promjene stanja;
* uređaj prima komande;
* uređaj vraća rezultate komandi;
* konfiguracija se mijenja preko Device Shadow-a;
* uređaj validira konfiguraciju;
* može se promijeniti period očitavanja;
* može se promijeniti temperaturna jedinica;
* postoji lokalna analitika;
* postoji monitoring tehničkog zdravlja uređaja;
* postoje upozorenja;
* podaci se čuvaju u DynamoDB;
* postoji istorija za posljednjih 30 dana;
* postoji funkcionalna web aplikacija;
* postoji vizuelna simulacija narukvice;
* postoje grafikoni;
* postoji rad bez internet veze;
* postoji offline red i naknadna sinhronizacija;
* postoji OTA paket verzije 2.0.0;
* OTA se pokreće kroz AWS IoT Jobs;
* paket se nalazi u privatnom S3 bucket-u;
* provjerava se SHA-256;
* postoji rollback;
* verzija 2.0.0 dodaje SpO2 senzor;
* frontend nakon nadogradnje prikazuje novu funkcionalnost;
* postoje osnovni unit i integracioni testovi;
* tajni podaci nisu postavljeni u Git.

======================================================================
37. FUNKCIONALNOSTI KOJE NISU OBAVEZNE
======================================

Sljedeće funkcionalnosti nisu dio obaveznog obima:

* fizička pametna narukvica;
* ESP32;
* Arduino;
* STM32;
* stvarni medicinski senzori;
* Android aplikacija;
* iOS aplikacija;
* React;
* mašinsko učenje;
* medicinska dijagnoza;
* bolnički informacioni sistem;
* automatsko pozivanje hitne pomoći;
* stvarni korisnički podaci;
* više hiljada uređaja;
* AWS Cognito autentikacija korisnika;
* produkciono cloud hostovanje web aplikacije;
* digitalno potpisivanje OTA paketa;
* detekcija pada;
* obavezni Greengrass.

Navedene stavke mogu biti navedene kao buduća proširenja.

======================================================================
38. FAZE IMPLEMENTACIJE
=======================

FAZA 0 – PROVJERA AWS NALOGA

* provjeriti pristup servisima;
* izabrati regiju;
* postaviti kontrolu troškova;
* napraviti osnovni AWS IoT test.

FAZA 1 – LOKALNI SIMULATOR

* napraviti strukturu projekta;
* napraviti state machine;
* napraviti senzore;
* napraviti ScenarioEngine;
* napraviti bateriju;
* napraviti lokalne logove.

FAZA 2 – LOKALNA ANALITIKA

* implementirati vremenske prozore;
* računati prosjek, minimum i maksimum;
* implementirati AlertManager;
* napisati unit testove.

FAZA 3 – AWS IoT CORE

* napraviti Thing;
* napraviti sertifikat;
* napraviti policy;
* povezati simulator;
* poslati prvu MQTT poruku;
* primiti prvu komandu.

FAZA 4 – DEVICE SHADOW

* implementirati desired;
* implementirati reported;
* implementirati delta;
* validirati konfiguraciju;
* testirati promjenu jedinice i perioda.

FAZA 5 – OFFLINE RAD

* napraviti SQLite bazu;
* napraviti OfflineQueue;
* implementirati reconnect;
* implementirati sinhronizaciju.

FAZA 6 – DYNAMODB I ISTORIJA

* napraviti tabele;
* napraviti IoT Rules;
* provjeriti upis;
* napraviti skript za 30 dana istorije.

FAZA 7 – FASTAPI BACKEND

* napraviti REST API;
* napraviti AWS servise;
* napraviti MQTT subscriber;
* napraviti WebSocket manager.

FAZA 8 – WEB FRONTEND

* napraviti dashboard;
* napraviti SVG/CSS narukvicu;
* napraviti animirano srce;
* napraviti kartice;
* napraviti grafikone;
* napraviti konfiguraciju;
* napraviti komande;
* napraviti Device Health prikaz.

FAZA 9 – OTA VERZIJA 1.0.0

* definisati release strukturu;
* napraviti OtaAgent;
* napraviti manifest;
* napraviti downloader;
* napraviti hash provjeru;
* napraviti rollback.

FAZA 10 – VERZIJA 2.0.0

* napraviti SpO2 senzor;
* napraviti SpO2 analitiku;
* napraviti novu konfiguraciju;
* napraviti novu frontend karticu;
* spakovati release.

FAZA 11 – AWS IoT JOBS

* postaviti paket u S3;
* napraviti IAM rolu;
* napraviti job dokument;
* izvršiti uspješan OTA;
* izvršiti neuspješan OTA;
* testirati rollback.

FAZA 12 – ZAVRŠNO TESTIRANJE

* unit testovi;
* integracioni testovi;
* end-to-end scenario;
* sigurnosna provjera;
* dokumentacija.

FAZA 13 – GREENGRASS, OPCIONO

Tek nakon završetka obaveznih faza.

======================================================================
39. DOKUMENTACIJA I DIJAGRAMI ZA DIPLOMSKI RAD
==============================================

U diplomskom radu treba prikazati najmanje:

* kontekst sistema;
* dijagram komponenti;
* modularnu arhitekturu uređaja;
* state machine dijagram;
* sekvencijalni dijagram slanja telemetrije;
* sekvencijalni dijagram komande;
* sekvencijalni dijagram Device Shadow konfiguracije;
* sekvencijalni dijagram OTA procesa;
* dijagram AWS resursa;
* model podataka;
* MQTT topic strukturu;
* sigurnosni model;
* testne scenarije;
* rezultate testiranja;
* prikaz web interfejsa;
* prikaz prije i poslije OTA nadogradnje;
* ograničenja sistema;
* moguće buduće nadogradnje.

======================================================================
40. VEZA IZMEĐU ZAHTJEVA PROFESORICE I IMPLEMENTACIJE
=====================================================

Zahtjev:
Simulacija uređaja.

Implementacija:
Python HealthBand simulator sa state machine logikom i ScenarioEngine modulom.

Zahtjev:
Uređaj zna svoje stanje.

Implementacija:
DeviceState enum i StateMachine modul.

Zahtjev:
Simulacija senzorskih vrijednosti.

Implementacija:
HeartRateSensor, SkinTemperatureSensor, StepCounterSensor, BatteryModel i kasnije SpO2Sensor.

Zahtjev:
Prijava promjena stanja.

Implementacija:
MQTT events poruke, health poruke i Device Shadow reported stanje.

Zahtjev:
Prihvatanje komandi.

Implementacija:
Custom MQTT commands/request i commands/response topic-i.

Zahtjev:
Konfiguracija perioda očitavanja.

Implementacija:
measurementIntervalSec preko Device Shadow desired/reported mehanizma.

Zahtjev:
Promjena fizičke jedinice.

Implementacija:
temperatureUnit CELSIUS ili FAHRENHEIT.

Zahtjev:
Cloud povezivanje.

Implementacija:
AWS IoT Core.

Zahtjev:
MQTT.

Implementacija:
AWS IoT Device SDK for Python v2.

Zahtjev:
MQTT preko TLS-a.

Implementacija:
AWS IoT Core TLS konekcija.

Zahtjev:
Autentikacija klijenta.

Implementacija:
X.509 sertifikat i IoT policy.

Zahtjev:
Lokalna analitika.

Implementacija:
AnalyticsManager računa prosjek, minimum, maksimum i druge agregate.

Zahtjev:
Istorija za posljednjih mjesec dana.

Implementacija:
DynamoDB, FastAPI history API, Chart.js i generator istorijskih podataka.

Zahtjev:
OTA.

Implementacija:
AWS IoT Jobs, privatni S3 bucket, OtaAgent, SHA-256 i rollback.

Zahtjev:
Nova funkcionalnost nakon OTA.

Implementacija:
Verzija 2.0.0 dodaje SpO2 senzor, analitiku, konfiguraciju i frontend prikaz.

Zahtjev:
Monitoring zdravlja uređaja.

Implementacija:
DeviceHealthMonitor i SensorHealthMonitor.

Zahtjev:
Modularna arhitektura.

Implementacija:
Odvojeni core, sensors, analytics, communication, commands, configuration, device_health, storage i ota moduli.

Zahtjev:
Greengrass kao opcija.

Implementacija:
Osnovna analitika radi bez Greengrass-a, a kasnije se može izdvojiti kao Greengrass komponenta.

======================================================================
41. SAŽETAK KOJI SE MOŽE OBJASNITI PROFESORICI
==============================================

Tema bi bila razvoj simuliranog wearable IoT uređaja za praćenje zdravstvenih i aktivnosti parametara korisnika. Uređaj bi bio implementiran kao modularna Python aplikacija i simulirao bi puls, temperaturu kože, broj koraka, aktivnost, bateriju i tehničko stanje senzora.

Uređaj bi imao jasno definisana stanja i različite simulacione scenarije, kao što su mirovanje, hodanje, trčanje, oporavak, kvar senzora i prekid internet veze.

Sa AWS IoT Core platformom povezivao bi se korišćenjem MQTT protokola preko TLS-a i autentifikovao X.509 sertifikatom. Uređaj bi slao telemetriju, agregirane podatke, upozorenja, događaje i izvještaje o sopstvenom tehničkom stanju.

Komande bi primao preko MQTT topic-a, dok bi se trajna konfiguracija, uključujući period očitavanja, period slanja, pragove i temperaturnu jedinicu, mijenjala korišćenjem AWS IoT Device Shadow mehanizma.

Na samom uređaju postojao bi lokalni analitički modul koji bi u definisanim vremenskim intervalima računao prosječnu, minimalnu i maksimalnu vrijednost parametara, broj koraka, nivo aktivnosti i kvalitet podataka.

Podaci bi se preko AWS IoT Rules mehanizma čuvali u DynamoDB bazi, a web aplikacija bi omogućavala prikaz trenutnih i istorijskih podataka za prethodnih 30 dana.

Web aplikacija bi imala vizuelnu simulaciju pametne narukvice, animirano srce, kartice senzora, grafikone, konfiguraciju, slanje komandi, monitoring uređaja i prikaz OTA procesa.

OTA nadogradnja bila bi realizovana pomoću AWS IoT Jobs i privatnog Amazon S3 bucket-a. Uređaj bi sa verzije 1.0.0 prešao na verziju 2.0.0, koja bi dodala podršku za novi simulirani SpO2 senzor, odgovarajuću analitiku i novi prikaz u korisničkoj aplikaciji. Paket bi prolazio provjeru SHA-256 integriteta, a u slučaju neuspjeha uređaj bi vraćao prethodnu verziju.

AWS IoT Greengrass ostao bi opciono proširenje u kojem bi se analitički modul izdvojio i izvršavao kao posebna edge komponenta.

======================================================================
42. UPUTSTVO ZA BUDUĆI AI THREAD
================================

AI asistent koji dobije ovu specifikaciju treba da zna:

1. Odabrana je wearable tema, a ne pametni semafor.

2. Uređaj je softverski simuliran i nema fizički hardver.

3. Simulator se radi u Pythonu.

4. Web backend se radi u Pythonu i FastAPI-ju.

5. Frontend se radi pomoću HTML-a, CSS-a, JavaScripta, SVG-a i Chart.js-a.

6. Cloud platforma je AWS.

7. MQTT broker je AWS IoT Core.

8. Komunikacija mora biti MQTT preko TLS-a.

9. Uređaj koristi X.509 sertifikat.

10. Konfiguracija se radi preko Device Shadow-a.

11. Komande se rade preko posebnih MQTT topic-a.

12. Podaci se čuvaju u DynamoDB.

13. IoT Rules prebacuje podatke u DynamoDB.

14. OTA paket se čuva u privatnom S3 bucket-u.

15. OTA se kontroliše preko AWS IoT Jobs.

16. Verzija 1.0.0 nema SpO2.

17. Verzija 2.0.0 dodaje SpO2 senzor i analitiku.

18. OTA mora stvarno dodati nove module.

19. Mora postojati SHA-256 provjera i rollback.

20. Mora postojati lokalna analitika.

21. Greengrass nije obavezan.

22. Mora postojati monitoring tehničkog zdravlja uređaja.

23. Mora postojati offline rad sa SQLite redom.

24. Web aplikacija mora prikazivati podatke u realnom vremenu preko WebSocket-a.

25. Podaci su potpuno simulirani i sistem nije medicinski uređaj.

26. Ne treba samovoljno dodavati Android aplikaciju, React, fizički hardver, mašinsko učenje ili druge velike funkcionalnosti.

27. Projekat treba izrađivati fazno.

28. Svaka završena faza treba biti pokretljiva i testirana prije prelaska na sljedeću.

29. Kod treba imati:

* jasne module;
* type hints;
* docstring komentare;
* centralizovan logging;
* validaciju;
* obradu grešaka;
* testove;
* konfiguraciju iz environment varijabli.

30. Tajni podaci nikada ne smiju biti upisani direktno u kod ili poslati na GitHub.

31. Prilikom slanja koda studentu, AI treba jasno navesti:

* putanju fajla;
* kompletan sadržaj fajla;
* komande za instalaciju;
* komande za pokretanje;
* šta treba očekivati kao rezultat.

32. Ne treba davati samo fragmente koda bez objašnjenja u koji fajl se postavljaju.

33. Ako profesorica promijeni specifikaciju, prvo treba ažurirati ovaj glavni dokument, a zatim implementaciju.

======================================================================
43. KONAČNA ODLUKA O OBIMU
==========================

OBAVEZNO:

* simulirani wearable uređaj;
* modularni Python kod;
* AWS IoT Core;
* MQTT preko TLS-a;
* X.509;
* telemetrija;
* komande;
* Device Shadow konfiguracija;
* promjena perioda očitavanja;
* Celzijus/Farenhajt;
* lokalna analitika;
* upozorenja;
* monitoring uređaja;
* DynamoDB;
* istorija 30 dana;
* web aplikacija;
* vizuelna simulacija;
* offline red;
* AWS IoT Jobs;
* S3;
* OTA 1.0.0 na 2.0.0;
* novi SpO2 modul;
* SHA-256;
* rollback;
* testiranje.

OPCIONO:

* Greengrass;
* digitalno potpisivanje paketa;
* detekcija pada;
* cloud hosting web aplikacije;
* korisnička autentikacija;
* Docker;
* dodatni senzori.

NIJE DIO TEME:

* fizička narukvica;
* stvarna medicinska mjerenja;
* dijagnostika;
* Android aplikacija;
* bolnički sistem;
* mašinsko učenje.

KRAJ SPECIFIKACIJE
