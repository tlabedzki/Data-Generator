# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Product catalog settings:

# Product names are always generated in this format:
# product_type brand product_series product_model
#
# Example:
# Smartphone Samsung Galaxy S23
#
# Every product type must define:
# - weight: product type share inside the category
# - price_range: net purchase price range in PLN
# - margin_range: gross margin range
# - brand_series_models: brand -> series -> models

product_catalog = {
    "Electronics": {
        "Smartphone": {
            "weight": 0.30,
            "price_range": (450, 4200),
            "margin_range": (0.10, 0.24),
            "brand_series_models": {
                "Samsung": {"Galaxy": ["S23", "S24", "A55", "A35", "Z Flip5"]},
                "Apple": {"iPhone": ["13", "14", "15", "15 Pro", "15 Pro Max"]},
                "Xiaomi": {"Redmi": ["Note 12", "Note 13", "12C"], "Xiaomi": ["13T", "14", "14 Ultra"]},
                "Sony": {"Xperia": ["10 V", "5 V", "1 V"]},
                "Huawei": {"Nova": ["10", "11", "Y91"]},
            },
        },
        "Laptop": {
            "weight": 0.22,
            "price_range": (1200, 7000),
            "margin_range": (0.08, 0.20),
            "brand_series_models": {
                "Lenovo": {"ThinkPad": ["T14", "X1 Carbon", "E16"], "IdeaPad": ["Slim 3", "Slim 5"]},
                "Apple": {"MacBook": ["Air 13", "Air 15", "Pro 14"]},
                "Dell": {"Inspiron": ["15", "16"], "XPS": ["13", "15"]},
                "HP": {"Pavilion": ["15", "Aero"], "EliteBook": ["840", "860"]},
                "Asus": {"VivoBook": ["15", "S14"], "ZenBook": ["14", "S13"]},
                "Acer": {"Aspire": ["5", "7"], "Swift": ["3", "Go"]},
            },
        },
        "Wireless Mouse": {
            "weight": 0.18,
            "price_range": (25, 260),
            "margin_range": (0.22, 0.42),
            "brand_series_models": {
                "Logitech": {"MX": ["Master 3S", "Anywhere 3S"], "M": ["185", "650"]},
                "Microsoft": {"Modern": ["Mobile", "Ergonomic"], "Surface": ["Arc", "Precision"]},
                "Dell": {"Premier": ["MS7421W"], "Mobile": ["MS3320W"]},
                "HP": {"Z": ["3700", "500"], "Spectre": ["Rechargeable"]},
            },
        },
        "Headphones": {
            "weight": 0.18,
            "price_range": (60, 1400),
            "margin_range": (0.18, 0.35),
            "brand_series_models": {
                "Sony": {"WH": ["1000XM4", "1000XM5"], "WF": ["C700N", "1000XM5"]},
                "Apple": {"AirPods": ["2", "3", "Pro 2"], "Beats": ["Studio Buds", "Solo 4"]},
                "JBL": {"Tune": ["520BT", "760NC"], "Live": ["660NC", "Pro 2"]},
                "Bose": {"QuietComfort": ["45", "Ultra"], "SoundSport": ["Free"]},
                "Philips": {"TAT": ["2206", "8506"], "Fidelio": ["L3"]},
            },
        },
        "Printer": {
            "weight": 0.12,
            "price_range": (220, 1600),
            "margin_range": (0.12, 0.26),
            "brand_series_models": {
                "HP": {"LaserJet": ["M110", "MFP M140"], "DeskJet": ["2720", "4120"]},
                "Canon": {"PIXMA": ["TS3450", "G3470"], "i-SENSYS": ["LBP6030"]},
                "Epson": {"EcoTank": ["L3250", "L4260"], "WorkForce": ["WF-2930"]},
                "Brother": {"DCP": ["1622WE", "T420W"], "HL": ["1222WE"]},
            },
        },
    },
    "Clothing": {
        "Sneakers": {
            "weight": 0.28,
            "price_range": (70, 260),
            "margin_range": (0.42, 0.60),
            "brand_series_models": {
                "Nike": {"Air Max": ["90", "270", "Excee"], "Court": ["Vision", "Legacy"]},
                "Adidas": {"Runfalcon": ["3.0", "4.0"], "Grand Court": ["Base", "Cloudfoam"]},
                "Puma": {"Rebound": ["Joy", "LayUp"], "Rider": ["Future", "Blktop"]},
                "New Balance": {"Classic": ["574", "373"], "Fresh Foam": ["Arishi", "Roav"]},
                "Reebok": {"Classic": ["Leather", "Nylon"], "Royal": ["Complete", "Glide"]},
            },
        },
        "T-Shirt": {
            "weight": 0.26,
            "price_range": (15, 90),
            "margin_range": (0.45, 0.65),
            "brand_series_models": {
                "H&M": {"Basic": ["Cotton", "Regular", "Slim"]},
                "Reserved": {"Essential": ["Crew", "Pocket", "Soft"]},
                "Sinsay": {"Daily": ["Classic", "Oversize", "Print"]},
                "Nike": {"Sportswear": ["Club", "Swoosh", "Air"]},
                "Adidas": {"Essentials": ["Logo", "3-Stripes", "Linear"]},
            },
        },
        "Jeans": {
            "weight": 0.18,
            "price_range": (70, 320),
            "margin_range": (0.42, 0.62),
            "brand_series_models": {
                "Levi's": {"501": ["Original", "Slim"], "511": ["Slim", "Dark"]},
                "Zara": {"Denim": ["Slim", "Straight", "Relaxed"]},
                "H&M": {"Regular": ["Blue", "Black"], "Slim": ["Stretch"]},
                "Reserved": {"Classic": ["Straight", "Tapered"]},
                "Mango": {"Denim": ["Mom Fit", "Wide Leg"]},
            },
        },
        "Jacket": {
            "weight": 0.16,
            "price_range": (80, 360),
            "margin_range": (0.40, 0.58),
            "brand_series_models": {
                "The North Face": {"Quest": ["Jacket", "Insulated"], "Resolve": ["2"]},
                "Columbia": {"Powder": ["Lite", "Pass"], "Watertight": ["II"]},
                "Reserved": {"Urban": ["Puffer", "Parka"]},
                "Zara": {"Outerwear": ["Bomber", "Puffer"]},
                "Patagonia": {"Torrentshell": ["3L"], "Nano Puff": ["Hoody"]},
            },
        },
        "Dress": {
            "weight": 0.12,
            "price_range": (60, 420),
            "margin_range": (0.46, 0.66),
            "brand_series_models": {
                "Zara": {"Evening": ["Midi", "Satin"], "Basic": ["Knit", "Shirt"]},
                "H&M": {"Classic": ["Wrap", "Ribbed"]},
                "Reserved": {"Elegant": ["Midi", "Floral"]},
                "Mango": {"Premium": ["Linen", "Satin"]},
                "Mohito": {"Chic": ["Cocktail", "Office"]},
            },
        },
    },
    "Home & Garden": {
        "Vacuum Cleaner": {
            "weight": 0.22,
            "price_range": (180, 2200),
            "margin_range": (0.22, 0.42),
            "brand_series_models": {
                "Dyson": {"V": ["8", "12", "15"]},
                "Philips": {"PowerPro": ["Compact", "Expert"], "Aqua": ["Trio"]},
                "Bosch": {"Serie": ["4", "6", "8"]},
                "Electrolux": {"Pure": ["D8", "Q9"], "Well": ["Q7"]},
                "Rowenta": {"X-Force": ["Flex", "Animal"]},
            },
        },
        "Coffee Machine": {
            "weight": 0.20,
            "price_range": (220, 3200),
            "margin_range": (0.20, 0.40),
            "brand_series_models": {
                "DeLonghi": {"Magnifica": ["Evo", "Start"], "Dinamica": ["Plus"]},
                "Philips": {"Series": ["2200", "3200", "5400"]},
                "Tefal": {"Evidence": ["Eco", "One"], "Essential": ["Compact"]},
                "Bosch": {"Vero": ["Cup", "Cafe"], "Tassimo": ["Happy"]},
                "Miele": {"CM": ["5310", "6360"]},
            },
        },
        "Garden Tool": {
            "weight": 0.20,
            "price_range": (25, 900),
            "margin_range": (0.28, 0.48),
            "brand_series_models": {
                "Gardena": {"Classic": ["Pruner", "Hose"], "Comfort": ["Sprayer"]},
                "Fiskars": {"Solid": ["Spade", "Rake"], "Xact": ["Weeder"]},
                "Black+Decker": {"Power": ["Trimmer", "Blower"]},
                "Bosch": {"EasyGarden": ["Shear", "Trimmer"]},
                "Stanley": {"FatMax": ["Knife", "Measure"]},
            },
        },
        "Kitchen Pan": {
            "weight": 0.20,
            "price_range": (30, 420),
            "margin_range": (0.30, 0.50),
            "brand_series_models": {
                "Tefal": {"Unlimited": ["Frypan", "Wok"], "Ingenio": ["Set"]},
                "Ambition": {"Silverstone": ["Pan", "Pot"], "Magnat": ["Frypan"]},
                "Russell Hobbs": {"Classic": ["Grill", "Pan"]},
                "Fiskars": {"Functional": ["Form", "Hard Face"]},
                "Brabantia": {"Tasty": ["Ceramic", "Steel"]},
            },
        },
        "Desk Lamp": {
            "weight": 0.18,
            "price_range": (25, 360),
            "margin_range": (0.30, 0.50),
            "brand_series_models": {
                "IKEA": {"TERTIAL": ["Work", "Desk"], "RANARP": ["Classic"]},
                "Philips": {"Hue": ["Go", "Bloom"], "EyeCare": ["Desk"]},
                "Philips": {"SceneSwitch": ["Desk", "LED"]},
                "Brabantia": {"Comfort": ["LED", "Office"]},
            },
        },
    },
    "Sports": {
        "Running Shoes": {
            "weight": 0.28,
            "price_range": (80, 330),
            "margin_range": (0.34, 0.52),
            "brand_series_models": {
                "Nike": {"Air Zoom": ["Pegasus", "Vomero"], "Revolution": ["6", "7"]},
                "Adidas": {"Ultraboost": ["Light", "22"], "Duramo": ["SL"]},
                "Asics": {"Gel": ["Cumulus", "Nimbus", "Pulse"]},
                "New Balance": {"Fresh Foam": ["1080", "880"], "FuelCell": ["Rebel"]},
                "Puma": {"Velocity": ["Nitro"], "Deviate": ["Nitro"]},
            },
        },
        "Fitness Mat": {
            "weight": 0.18,
            "price_range": (25, 180),
            "margin_range": (0.35, 0.55),
            "brand_series_models": {
                "Decathlon": {"Domyos": ["Comfort", "Essential"]},
                "Spokey": {"Softmat": ["Pro", "Basic"]},
                "Martes": {"Active": ["Yoga", "Fitness"]},
                "Adidas": {"Training": ["Mat", "Core"]},
            },
        },
        "Mountain Bike": {
            "weight": 0.16,
            "price_range": (900, 4200),
            "margin_range": (0.20, 0.34),
            "brand_series_models": {
                "Kross": {"Level": ["2.0", "4.0", "6.0"]},
                "Giant": {"Talon": ["1", "2", "3"]},
                "Trek": {"Marlin": ["5", "6", "7"]},
                "Decathlon": {"Rockrider": ["ST100", "ST530"]},
            },
        },
        "Tennis Racket": {
            "weight": 0.16,
            "price_range": (120, 850),
            "margin_range": (0.30, 0.48),
            "brand_series_models": {
                "Wilson": {"Blade": ["98", "100"], "Clash": ["100"]},
                "Head": {"Speed": ["MP", "Team"], "Radical": ["MP"]},
                "Yonex": {"Ezone": ["98", "100"], "VCore": ["100"]},
                "Decathlon": {"Artengo": ["TR160", "TR930"]},
            },
        },
        "Backpack": {
            "weight": 0.22,
            "price_range": (70, 520),
            "margin_range": (0.34, 0.54),
            "brand_series_models": {
                "The North Face": {"Borealis": ["Classic", "Mini"], "Jester": ["Backpack"]},
                "Columbia": {"Atlas": ["Explorer"], "Trail": ["Pack"]},
                "Patagonia": {"Refugio": ["26L", "30L"]},
                "Salomon": {"Trailblazer": ["10", "20"]},
                "4F": {"Trekking": ["Urban", "Mountain"]},
            },
        },
    },
    "Beauty": {
        "Face Cream": {
            "weight": 0.26,
            "price_range": (10, 180),
            "margin_range": (0.52, 0.72),
            "brand_series_models": {
                "Nivea": {"Soft": ["Hydrating", "Fresh"], "Q10": ["Anti-Wrinkle", "Firming"]},
                "L'Oreal": {"Revitalift": ["Day Cream", "Night Cream"], "Hydra": ["Genius", "Glow"]},
                "Ziaja": {"Classic": ["Goat Milk", "Olive"], "Pro": ["Sensitive", "Repair"]},
                "Vichy": {"Aqualia": ["Thermal"], "Liftactiv": ["Collagen"]},
                "La Roche-Posay": {"Toleriane": ["Sensitive"], "Effaclar": ["Duo"]},
            },
        },
        "Mascara": {
            "weight": 0.18,
            "price_range": (12, 120),
            "margin_range": (0.55, 0.72),
            "brand_series_models": {
                "Maybelline": {"Lash": ["Sensational", "Sky High"], "Colossal": ["Black"]},
                "L'Oreal": {"Volume": ["Million Lashes"], "Telescopic": ["Lift"]},
                "Eveline": {"Extension": ["Volume", "Curl"]},
                "Dior": {"Diorshow": ["Iconic", "Pump"]},
                "Chanel": {"Le Volume": ["Noir", "Waterproof"]},
            },
        },
        "Shampoo": {
            "weight": 0.22,
            "price_range": (8, 90),
            "margin_range": (0.45, 0.65),
            "brand_series_models": {
                "Pantene": {"Pro-V": ["Repair", "Volume"]},
                "Garnier": {"Fructis": ["Strength", "Hydra"]},
                "Nivea": {"Care": ["Shine", "Fresh"]},
                "L'Oreal": {"Elseve": ["Dream Long", "Color-Vive"]},
                "Yves Rocher": {"Botanical": ["Repair", "Volume"]},
            },
        },
        "Perfume": {
            "weight": 0.14,
            "price_range": (80, 520),
            "margin_range": (0.58, 0.76),
            "brand_series_models": {
                "Dior": {"Sauvage": ["EDT", "Elixir"], "J'adore": ["EDP"]},
                "Chanel": {"Chance": ["Eau Tendre"], "Bleu": ["EDP"]},
                "Yves Rocher": {"Comme": ["Evidence"], "Monoi": ["Eau"]},
                "Lancome": {"La Vie": ["Belle"], "Idole": ["Now"]},
                "Estee Lauder": {"Beautiful": ["Magnolia"], "Pleasures": ["EDP"]},
            },
        },
        "Lipstick": {
            "weight": 0.20,
            "price_range": (8, 80),
            "margin_range": (0.55, 0.74),
            "brand_series_models": {
                "MAC": {"Matte": ["Ruby Woo", "Velvet Teddy"], "Love Me": ["Coffee"]},
                "Maybelline": {"SuperStay": ["Matte Ink"], "Color": ["Sensational"]},
                "Revlon": {"Super Lustrous": ["Rose", "Red"]},
                "Inglot": {"Freedom": ["Matte", "Satin"]},
                "Eveline": {"Wonder": ["Match", "Matte"]},
            },
        },
    },
    "Toys": {
        "Building Blocks": {
            "weight": 0.34,
            "price_range": (25, 650),
            "margin_range": (0.32, 0.50),
            "brand_series_models": {
                "Lego": {"City": ["Police", "Fire Station"], "Technic": ["Car", "Crane"], "Friends": ["Cafe"]},
                "Cobi": {"Historical": ["Tank", "Plane"], "Youngtimer": ["Car"]},
                "Playmobil": {"City Life": ["Hospital"], "Pirates": ["Ship"]},
            },
        },
        "Board Game": {
            "weight": 0.24,
            "price_range": (30, 220),
            "margin_range": (0.35, 0.52),
            "brand_series_models": {
                "Trefl": {"Family": ["Quiz", "Adventure"]},
                "Ravensburger": {"Classic": ["Labyrinth", "Memory"]},
                "Hasbro": {"Monopoly": ["Classic", "Junior"], "Cluedo": ["Classic"]},
                "Clementoni": {"Fun": ["Logic", "Quiz"]},
            },
        },
        "Doll": {
            "weight": 0.18,
            "price_range": (35, 260),
            "margin_range": (0.35, 0.52),
            "brand_series_models": {
                "Barbie": {"Fashionistas": ["Doll", "Set"], "Dreamtopia": ["Princess"]},
                "Mattel": {"Polly Pocket": ["Compact", "Set"]},
                "Fisher-Price": {"Little People": ["Family", "Playset"]},
            },
        },
        "Toy Car": {
            "weight": 0.24,
            "price_range": (10, 180),
            "margin_range": (0.32, 0.50),
            "brand_series_models": {
                "Hot Wheels": {"Premium": ["Car", "Track"], "City": ["Set"]},
                "Mattel": {"Matchbox": ["Car", "Garage"]},
                "Spin Master": {"Monster Jam": ["Truck"]},
                "Brio": {"Classic": ["Train", "Track"]},
            },
        },
    },
    "Automotive": {
        "Engine Oil": {
            "weight": 0.24,
            "price_range": (35, 220),
            "margin_range": (0.18, 0.32),
            "brand_series_models": {
                "Castrol": {"Edge": ["5W30", "5W40"], "Magnatec": ["10W40"]},
                "Mobil": {"Super": ["3000", "2000"], "1": ["ESP"]},
                "Motul": {"8100": ["X-clean", "Eco"], "Specific": ["504"]},
                "Shell": {"Helix": ["Ultra", "HX7"]},
            },
        },
        "Car Tire": {
            "weight": 0.24,
            "price_range": (180, 900),
            "margin_range": (0.15, 0.28),
            "brand_series_models": {
                "Michelin": {"Primacy": ["4", "4+"], "Pilot": ["Sport 5"]},
                "Goodyear": {"EfficientGrip": ["Performance"], "Vector": ["4Seasons"]},
                "Continental": {"PremiumContact": ["7"], "WinterContact": ["TS870"]},
                "Pirelli": {"Cinturato": ["P7"], "Powergy": ["Summer"]},
                "Hankook": {"Ventus": ["Prime", "S1"], "Kinergy": ["Eco"]},
            },
        },
        "Brake Pads": {
            "weight": 0.20,
            "price_range": (60, 420),
            "margin_range": (0.22, 0.38),
            "brand_series_models": {
                "Bosch": {"QuietCast": ["Front", "Rear"]},
                "Brembo": {"Prime": ["Front", "Rear"]},
                "Ferodo": {"Premier": ["Front"], "Eco": ["Rear"]},
                "Valeo": {"First": ["Front", "Rear"]},
            },
        },
        "Car Battery": {
            "weight": 0.16,
            "price_range": (180, 750),
            "margin_range": (0.15, 0.28),
            "brand_series_models": {
                "Varta": {"Blue Dynamic": ["E11", "D24"], "Silver Dynamic": ["AGM"]},
                "Bosch": {"S4": ["60Ah", "74Ah"], "S5": ["AGM"]},
                "Continental": {"Start": ["60Ah", "70Ah"]},
            },
        },
        "Wiper Blades": {
            "weight": 0.16,
            "price_range": (20, 160),
            "margin_range": (0.25, 0.42),
            "brand_series_models": {
                "Bosch": {"Aerotwin": ["Set", "Front"], "Eco": ["Pair"]},
                "Valeo": {"Silencio": ["Set"], "First": ["Pair"]},
                "Denso": {"Hybrid": ["Set"], "Flat": ["Pair"]},
            },
        },
    },
    "Books & Media": {
        "Book": {
            "weight": 0.42,
            "price_range": (12, 90),
            "margin_range": (0.18, 0.34),
            "brand_series_models": {
                "Empik": {
                    "Biblioteczka Opracowan": ["Lalka", "Zbrodnia i kara"],
                    "Bestseller": ["Atomic Habits", "Glukozowa rewolucja"],
                },
                "Znak": {
                    "Litera Nova": ["Beksinscy. Portret podwojny", "Chlopki. Opowiesc o naszych babkach"],
                    "Horyzont": ["Kajs. Opowiesc o Gornym Slasku", "Wielka trwoga"],
                },
                "Helion": {
                    "Onepress": ["Finansowa forteca", "Esencjalista"],
                    "Programowanie": ["Python. Kurs dla nauczycieli i studentow", "Algorytmy w Pythonie"],
                    "Dla poczatkujacych": ["Po prostu Python"],
                },
                "PWN": {
                    "Slowniki": ["Slownik angielsko-polski polsko-angielski", "Wielki slownik polsko-angielski Oxford"],
                    "Akademicka": ["Historia filozofii", "Socjologia. Analiza spoleczenstwa"],
                },
                "Rebis": {
                    "Wehikul Czasu": ["Diuna", "Fundacja"],
                    "Historia": ["Sapiens. Od zwierzat do bogow", "Homo deus"],
                },
            },
        },
        "Comic Book": {
            "weight": 0.18,
            "price_range": (15, 140),
            "margin_range": (0.18, 0.35),
            "brand_series_models": {
                "Marvel": {
                    "Spider-Man": ["Ostatnie lowy Kravena", "Niebieski"],
                    "Avengers": ["Wojna bez konca", "Koniec gry"],
                },
                "DC": {
                    "Batman": ["Rok pierwszy", "Hush"],
                    "Superman": ["Czerwony syn", "Dziedzictwo"],
                },
                "Egmont": {
                    "Asteriks": ["Asteriks i Kleopatra", "Asteriks u Brytow"],
                    "Kajko i Kokosz": ["Szkola latania", "Wielki turniej"],
                },
            },
        },
        "Music Album": {
            "weight": 0.16,
            "price_range": (18, 120),
            "margin_range": (0.16, 0.30),
            "brand_series_models": {
                "Sony Music": {
                    "Legacy": ["The Essential Michael Jackson", "The Wall"],
                    "Columbia": ["Kind of Blue", "Highway 61 Revisited"],
                },
                "Universal Music": {
                    "Polydor": ["Abbey Road", "Nevermind"],
                    "Deluxe": ["A Night at the Opera", "Brothers in Arms"],
                },
                "Agora": {
                    "Polska Muzyka": ["Maanam The Best", "Republika 82-85"],
                    "Koncerty": ["MTV Unplugged Hey", "Live Pol'and'Rock"],
                },
            },
        },
        "Board Book": {
            "weight": 0.24,
            "price_range": (8, 55),
            "margin_range": (0.20, 0.38),
            "brand_series_models": {
                "Egmont": {
                    "Akademia Madrego Dziecka": ["Pierwsze slowa. Zwierzeta", "Pierwsze slowa. Kolory"],
                    "Disney Baby": ["Myszka Miki. Moje pierwsze slowa", "Kubus i przyjaciele. Liczby"],
                },
                "PWN": {
                    "Junior": ["Moj pierwszy slownik obrazkowy", "Alfabet przedszkolaka"],
                },
                "HarperCollins": {
                    "Basia": ["Basia i zwierzaki", "Basia i przedszkole"],
                    "Paddington": ["Paddington. Moje pierwsze slowa"],
                },
            },
        },
    },
    "Health": {
        "Vitamin Supplement": {
            "weight": 0.26,
            "price_range": (8, 120),
            "margin_range": (0.48, 0.68),
            "brand_series_models": {
                "Doppelherz": {"Aktiv": ["Magnesium", "Omega"], "System": ["Immune"]},
                "Swanson": {"Premium": ["D3", "Omega"], "Ultra": ["Q10"]},
                "Solgar": {"Classic": ["Vitamin C", "Zinc"]},
                "Naturell": {"Daily": ["D3", "Magnesium"]},
                "Olimp Labs": {"Gold": ["Vita-Min", "Omega"]},
            },
        },
        "Pain Relief": {
            "weight": 0.22,
            "price_range": (5, 45),
            "margin_range": (0.35, 0.55),
            "brand_series_models": {
                "Apap": {"Classic": ["Tablets", "Extra"]},
                "Ibuprom": {"Max": ["Tablets", "Sprint"]},
                "Hasco-Lek": {"Hascovir": ["Control"], "Classic": ["Tabs"]},
                "Aflofarm": {"Rapid": ["Caps", "Tabs"]},
            },
        },
        "Toothpaste": {
            "weight": 0.22,
            "price_range": (5, 35),
            "margin_range": (0.38, 0.58),
            "brand_series_models": {
                "Colgate": {"Total": ["Original", "Whitening"], "Max": ["Fresh"]},
                "Sensodyne": {"Repair": ["Protect"], "Pronamel": ["Daily"]},
                "Oral-B": {"Pro": ["Expert", "Gum"]},
            },
        },
        "Blood Pressure Monitor": {
            "weight": 0.14,
            "price_range": (80, 420),
            "margin_range": (0.25, 0.45),
            "brand_series_models": {
                "Omron": {"M": ["2", "3", "7"], "RS": ["3"]},
                "Accu-Chek": {"Instant": ["Monitor"], "Guide": ["Set"]},
            },
        },
        "Cold Remedy": {
            "weight": 0.16,
            "price_range": (8, 65),
            "margin_range": (0.35, 0.55),
            "brand_series_models": {
                "Vicks": {"Vapo": ["Rub", "Drops"], "Sinex": ["Spray"]},
                "Rutinoscorbin": {"Classic": ["Tablets"], "Extra": ["Zinc"]},
                "Aflofarm": {"Grip": ["Tabs", "Hot"]},
            },
        },
    },
    "Pet Supplies": {
        "Dog Food": {
            "weight": 0.34,
            "price_range": (12, 280),
            "margin_range": (0.28, 0.48),
            "brand_series_models": {
                "Royal Canin": {"Size": ["Mini Adult", "Maxi Adult"], "Breed": ["Labrador"]},
                "Purina": {"One": ["Adult", "Junior"], "Pro Plan": ["Sensitive"]},
                "Pedigree": {"Vital": ["Adult", "Junior"], "Dentastix": ["Medium"]},
                "Brit": {"Care": ["Adult", "Puppy"]},
                "Acana": {"Classic": ["Prairie", "Wild Coast"]},
            },
        },
        "Cat Food": {
            "weight": 0.30,
            "price_range": (8, 220),
            "margin_range": (0.28, 0.48),
            "brand_series_models": {
                "Whiskas": {"Classic": ["Chicken", "Beef"], "Junior": ["Poultry"]},
                "Purina": {"One": ["Sterilcat", "Indoor"], "Gourmet": ["Gold"]},
                "Royal Canin": {"Feline": ["Indoor", "Sterilised"]},
                "Animonda": {"Carny": ["Adult", "Kitten"]},
                "Josera": {"Catelux": ["Adult"], "Culinesse": ["Salmon"]},
            },
        },
        "Pet Toy": {
            "weight": 0.18,
            "price_range": (8, 90),
            "margin_range": (0.35, 0.55),
            "brand_series_models": {
                "Trixie": {"Fun": ["Ball", "Rope"], "Premium": ["Toy"]},
                "Zolux": {"Classic": ["Mouse", "Bone"]},
                "Catit": {"Senses": ["Circuit", "Ball"]},
            },
        },
        "Pet Litter": {
            "weight": 0.18,
            "price_range": (15, 110),
            "margin_range": (0.25, 0.42),
            "brand_series_models": {
                "Vitakraft": {"Classic": ["Litter"], "Compact": ["Fresh"]},
                "Versele-Laga": {"Prestige": ["Litter"], "Nature": ["Wood"]},
                "Trixie": {"Fresh": ["Compact", "Natural"]},
            },
        },
    },
    "Baby & Kids": {
        "Diapers": {
            "weight": 0.28,
            "price_range": (25, 120),
            "margin_range": (0.22, 0.40),
            "brand_series_models": {
                "Pampers": {"Premium": ["Care", "Protection"], "Active": ["Baby"]},
                "Huggies": {"Elite": ["Soft"], "Extra": ["Care"]},
                "Dada": {"Extra": ["Care", "Soft"]},
            },
        },
        "Baby Formula": {
            "weight": 0.22,
            "price_range": (35, 110),
            "margin_range": (0.18, 0.34),
            "brand_series_models": {
                "Bebilon": {"Profutura": ["1", "2"], "Advance": ["3"]},
                "Nan": {"Optipro": ["1", "2"], "Expert": ["HA"]},
                "HiPP": {"Bio": ["Combiotik", "Organic"]},
            },
        },
        "Baby Bottle": {
            "weight": 0.18,
            "price_range": (15, 95),
            "margin_range": (0.35, 0.55),
            "brand_series_models": {
                "Avent": {"Natural": ["125ml", "260ml"], "Anti-Colic": ["260ml"]},
                "Canpol": {"EasyStart": ["Bottle", "Set"], "Royal": ["Baby"]},
                "Chicco": {"NaturalFeeling": ["Bottle"]},
            },
        },
        "Car Seat": {
            "weight": 0.16,
            "price_range": (250, 1600),
            "margin_range": (0.22, 0.40),
            "brand_series_models": {
                "Maxi-Cosi": {"Pebble": ["360"], "Titan": ["Plus"]},
                "Cybex": {"Solution": ["S2", "T"], "Sirona": ["T"]},
                "Britax Romer": {"Kidfix": ["i-Size"], "Dualfix": ["M"]},
            },
        },
        "Baby Stroller": {
            "weight": 0.16,
            "price_range": (350, 2200),
            "margin_range": (0.24, 0.42),
            "brand_series_models": {
                "Kinderkraft": {"Grande": ["Plus"], "Nubi": ["2"]},
                "Chicco": {"Goody": ["Plus"], "Liteway": ["4"]},
                "Cybex": {"Balios": ["S Lux"], "Eezy": ["S Twist"]},
            },
        },
    },
    "Office": {
        "Notebook": {
            "weight": 0.24,
            "price_range": (3, 35),
            "margin_range": (0.25, 0.45),
            "brand_series_models": {
                "Oxford": {"Classic": ["A5", "A4"], "Touch": ["A5"]},
                "Leitz": {"Complete": ["A5"], "Office": ["A4"]},
                "Esselte": {"Standard": ["A4", "A5"]},
            },
        },
        "Pen": {
            "weight": 0.22,
            "price_range": (1, 45),
            "margin_range": (0.30, 0.55),
            "brand_series_models": {
                "Bic": {"Cristal": ["Blue", "Black"], "Velocity": ["Gel"]},
                "Pilot": {"G2": ["07", "05"], "Frixion": ["Ball"]},
                "Parker": {"Jotter": ["Classic", "XL"], "IM": ["Black"]},
                "Stabilo": {"Point": ["88"], "Boss": ["Original"]},
            },
        },
        "Office Chair": {
            "weight": 0.18,
            "price_range": (120, 1200),
            "margin_range": (0.22, 0.40),
            "brand_series_models": {
                "Fellowes": {"Ergo": ["Office", "Pro"]},
                "Fellowes": {"Professional": ["Chair", "Ergo"]},
                "Leitz": {"Ergo": ["Cosy"]},
            },
        },
        "Monitor": {
            "weight": 0.18,
            "price_range": (300, 1600),
            "margin_range": (0.12, 0.26),
            "brand_series_models": {
                "Dell": {"UltraSharp": ["24", "27"], "P": ["2422H"]},
                "HP": {"M": ["24f", "27f"], "Z": ["24n"]},
                "Lenovo": {"ThinkVision": ["T24", "P27"]},
                "Epson": {"Work": ["Display"]},
            },
        },
        "Paper Shredder": {
            "weight": 0.18,
            "price_range": (100, 850),
            "margin_range": (0.18, 0.35),
            "brand_series_models": {
                "Fellowes": {"Powershred": ["36C", "60Cs"], "AutoMax": ["100M"]},
                "Leitz": {"IQ": ["Home", "Office"]},
                "Esselte": {"Secure": ["Basic", "Pro"]},
            },
        },
    },
    "Jewelry & Accessories": {
        "Watch": {
            "weight": 0.32,
            "price_range": (80, 1800),
            "margin_range": (0.40, 0.62),
            "brand_series_models": {
                "Casio": {"G-Shock": ["GA-2100", "5600"], "Vintage": ["A168"]},
                "Fossil": {"Grant": ["Chronograph"], "Machine": ["FS4656"]},
                "Timex": {"Expedition": ["Scout"], "Weekender": ["Classic"]},
                "Seiko": {"5": ["Sports"], "Presage": ["Cocktail"]},
                "Michael Kors": {"Parker": ["Gold"], "Runway": ["Silver"]},
            },
        },
        "Sunglasses": {
            "weight": 0.24,
            "price_range": (40, 700),
            "margin_range": (0.45, 0.68),
            "brand_series_models": {
                "Ray-Ban": {"Aviator": ["Classic"], "Wayfarer": ["Original"]},
                "Polaroid": {"PLD": ["Classic", "Sport"]},
                "Vogue": {"VO": ["Cat Eye", "Round"]},
                "Guess": {"GU": ["Fashion", "Pilot"]},
            },
        },
        "Bracelet": {
            "weight": 0.22,
            "price_range": (35, 900),
            "margin_range": (0.50, 0.70),
            "brand_series_models": {
                "Pandora": {"Moments": ["Heart", "Charm"], "Timeless": ["Silver"]},
                "Apart": {"Classic": ["Silver", "Gold"], "Modern": ["Chain"]},
                "W.Kruk": {"Zodiak": ["Bracelet"], "Classic": ["Gold"]},
                "Swarovski": {"Matrix": ["Tennis"], "Una": ["Angel"]},
            },
        },
        "Handbag": {
            "weight": 0.22,
            "price_range": (80, 1500),
            "margin_range": (0.45, 0.68),
            "brand_series_models": {
                "Guess": {"Noelle": ["Mini", "Elite"], "Vikky": ["Tote"]},
                "Michael Kors": {"Jet Set": ["Travel"], "Mercer": ["Medium"]},
                "Tous": {"Kaos": ["Mini", "Icon"], "Audree": ["Bag"]},
                "Swarovski": {"Crystal": ["Pouch"]},
            },
        },
    },
    "Furniture": {
        "Office Desk": {
            "weight": 0.22,
            "price_range": (120, 1200),
            "margin_range": (0.28, 0.46),
            "brand_series_models": {
                "IKEA": {"MALM": ["Desk"], "LAGKAPTEN": ["Desk"]},
                "Black Red White": {"Office": ["Desk", "Corner"]},
                "VOX": {"Simple": ["Desk"], "Young": ["Desk"]},
                "Selsey": {"Modern": ["Desk"]},
            },
        },
        "Sofa": {
            "weight": 0.24,
            "price_range": (600, 4500),
            "margin_range": (0.30, 0.50),
            "brand_series_models": {
                "IKEA": {"KIVIK": ["2-seat", "Corner"], "FRIHETEN": ["Sofa Bed"]},
                "Agata": {"Comfort": ["Sofa", "Corner"]},
                "Kler": {"Premium": ["Sofa", "Corner"]},
                "Forte": {"Living": ["Sofa"]},
            },
        },
        "Dining Chair": {
            "weight": 0.20,
            "price_range": (60, 550),
            "margin_range": (0.28, 0.48),
            "brand_series_models": {
                "IKEA": {"ADDE": ["Chair"], "BERGMUND": ["Chair"]},
                "Signal": {"H-261": ["Chair"], "Milo": ["Chair"]},
                "Halmar": {"K303": ["Chair"], "Borys": ["Chair"]},
                "Bodzio": {"Classic": ["Chair"]},
            },
        },
        "Mattress": {
            "weight": 0.18,
            "price_range": (250, 2500),
            "margin_range": (0.32, 0.52),
            "brand_series_models": {
                "Hilding": {"Melody": ["Comfort"], "Fandango": ["Hybrid"]},
                "Tempur": {"Original": ["Elite"], "Cloud": ["Supreme"]},
                "IKEA": {"VALEVAG": ["Pocket"], "ABYGDA": ["Foam"]},
            },
        },
        "Wardrobe": {
            "weight": 0.16,
            "price_range": (300, 2600),
            "margin_range": (0.28, 0.46),
            "brand_series_models": {
                "Black Red White": {"Flex": ["Wardrobe"], "Malta": ["Wardrobe"]},
                "Forte": {"Lyon": ["Wardrobe"], "Hud": ["Wardrobe"]},
                "Bodzio": {"Classic": ["Wardrobe"]},
                "Meble Wojcik": {"Trend": ["Wardrobe"]},
            },
        },
    },
    "DIY Tools": {
        "Cordless Drill": {
            "weight": 0.28,
            "price_range": (120, 1200),
            "margin_range": (0.20, 0.38),
            "brand_series_models": {
                "Bosch": {"EasyDrill": ["18V", "1200"], "Professional": ["GSR"]},
                "Makita": {"LXT": ["DDF482", "DHP485"]},
                "DeWalt": {"XR": ["DCD791", "DCD796"]},
                "Ryobi": {"ONE+": ["Drill", "Hammer"]},
                "Milwaukee": {"M18": ["Fuel", "Compact"]},
            },
        },
        "Screwdriver Set": {
            "weight": 0.20,
            "price_range": (15, 220),
            "margin_range": (0.28, 0.48),
            "brand_series_models": {
                "Stanley": {"FatMax": ["Set", "Precision"]},
                "Wera": {"Kraftform": ["Set", "VDE"]},
                "Knipex": {"Classic": ["Set"]},
                "Topex": {"Basic": ["Set"]},
                "Yato": {"Pro": ["Set"]},
            },
        },
        "Angle Grinder": {
            "weight": 0.18,
            "price_range": (90, 850),
            "margin_range": (0.20, 0.36),
            "brand_series_models": {
                "Bosch": {"Professional": ["GWS"], "Easy": ["Grind"]},
                "Makita": {"GA": ["5030", "9020"]},
                "DeWalt": {"XR": ["DCG405"], "DWE": ["4157"]},
                "Metabo": {"W": ["750", "850"]},
            },
        },
        "Tool Box": {
            "weight": 0.18,
            "price_range": (25, 360),
            "margin_range": (0.25, 0.45),
            "brand_series_models": {
                "Stanley": {"Classic": ["16in", "19in"], "FatMax": ["Pro"]},
                "Yato": {"System": ["Box", "Case"]},
                "Topex": {"Basic": ["Box"]},
                "Fiskars": {"Solid": ["Case"]},
            },
        },
        "Saw": {
            "weight": 0.16,
            "price_range": (25, 900),
            "margin_range": (0.22, 0.40),
            "brand_series_models": {
                "Bosch": {"Professional": ["GKS", "GST"]},
                "Makita": {"JR": ["3051"], "HS": ["7601"]},
                "DeWalt": {"DWE": ["560", "305"]},
                "Einhell": {"TC": ["CS", "JS"]},
            },
        },
    },
}

def validate_product_catalog(catalog):
    for category, product_types in catalog.items():
        if not product_types:
            raise ValueError(f"Category has no product types: {category}")
        for product_type, definition in product_types.items():
            required_keys = {"weight", "price_range", "margin_range", "brand_series_models"}
            missing_keys = required_keys - set(definition)
            if missing_keys:
                raise ValueError(f"Missing keys for {category}/{product_type}: {missing_keys}")
            if not definition["brand_series_models"]:
                raise ValueError(f"Product type has no brands: {category}/{product_type}")
            for brand, series_map in definition["brand_series_models"].items():
                if not series_map:
                    raise ValueError(f"Brand has no series: {category}/{product_type}/{brand}")
                for series, models in series_map.items():
                    if not series:
                        raise ValueError(f"Empty series for {category}/{product_type}/{brand}")
                    if not models:
                        raise ValueError(f"Series has no models: {category}/{product_type}/{brand}/{series}")
                    for model in models:
                        if not model:
                            raise ValueError(f"Empty model for {category}/{product_type}/{brand}/{series}")

validate_product_catalog(product_catalog)
