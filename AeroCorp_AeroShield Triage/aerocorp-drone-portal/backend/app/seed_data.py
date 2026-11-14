from datetime import datetime, timezone

CATEGORIES = [
    "Consumer & creator",
    "FPV & racing",
    "Enterprise inspection",
    "Mapping & survey",
    "Agriculture",
    "Delivery & logistics",
    "Long-endurance",
]

DRONES = [
    # ------------------------------------------------------------------ Consumer & creator
    dict(
        name="DJI Mavic 3 Pro", manufacturer="DJI", category="Consumer & creator",
        description="A folding triple-camera drone with a large-sensor main camera and two telephoto lenses. "
                    "Popular with filmmakers who need several focal lengths from one flight.",
        specs=dict(flight_time_min=43, max_range_km=15, max_speed_kmh=75, weight_kg=0.958,
                   camera="4/3-inch main + medium tele + tele"),
        price_usd=2199, wiki_title="DJI Mavic 3", source_url="https://www.dji.com/mavic-3-pro",
    ),
    dict(
        name="DJI Mini 4 Pro", manufacturer="DJI", category="Consumer & creator",
        description="A sub-250 g folding drone with obstacle sensing in all directions. "
                    "Light enough to fly under relaxed registration rules in many countries.",
        specs=dict(flight_time_min=34, max_range_km=20, max_speed_kmh=57, weight_kg=0.249,
                   camera="1/1.3-inch, 4K/60 HDR"),
        price_usd=759, wiki_title="DJI Mini", source_url="https://www.dji.com/mini-4-pro",
    ),
    # ------------------------------------------------------------------ FPV & racing
    dict(
        name="DJI Avata 2", manufacturer="DJI", category="FPV & racing",
        description="A ducted-propeller FPV drone flown with goggles and a motion controller. "
                    "The guards make it forgiving for pilots learning close-in flying.",
        specs=dict(flight_time_min=23, max_range_km=13, max_speed_kmh=97, weight_kg=0.377,
                   camera="1/1.3-inch, 4K/60"),
        price_usd=999, wiki_title="DJI Avata", source_url="https://www.dji.com/avata-2",
    ),
    # ------------------------------------------------------------------ Enterprise inspection
    dict(
        name="DJI Matrice 350 RTK", manufacturer="DJI", category="Enterprise inspection",
        description="A weather-sealed enterprise platform that carries up to three payloads, including zoom, "
                    "thermal and laser rangefinder cameras. Used for power-line, tower and facade inspection.",
        specs=dict(flight_time_min=55, max_range_km=20, max_speed_kmh=83, weight_kg=6.47, payload_kg=2.7,
                   ip_rating="IP55"),
        price_usd=None, wiki_title="DJI Matrice 300 RTK", source_url="https://enterprise.dji.com/matrice-350-rtk",
    ),
    dict(
        name="Skydio X10", manufacturer="Skydio", category="Enterprise inspection",
        description="An autonomy-first drone with six navigation cameras that keeps flying close to structures "
                    "without GPS. Carries visual and thermal cameras for public-safety and infrastructure teams.",
        specs=dict(flight_time_min=40, max_speed_kmh=72, camera="Visual + thermal"),
        price_usd=None, wiki_title="Skydio", source_url="https://www.skydio.com/x10",
    ),
    dict(
        name="Parrot ANAFI USA", manufacturer="Parrot", category="Enterprise inspection",
        description="A compact folding drone built for government and enterprise use, with a 32x zoom camera and "
                    "a thermal sensor. Designed and manufactured with a secure data-handling approach.",
        specs=dict(flight_time_min=32, max_range_km=4, max_speed_kmh=55, weight_kg=0.5,
                   camera="32x zoom + thermal"),
        price_usd=None, wiki_title="Parrot Anafi", source_url="https://www.parrot.com/en/drones/anafi-usa",
    ),
    dict(
        name="Autel EVO Max 4T", manufacturer="Autel Robotics", category="Enterprise inspection",
        description="A foldable inspection drone that combines wide, zoom, thermal and laser-ranging sensors in "
                    "one gimbal. Obstacle avoidance uses a mix of cameras and millimetre-wave radar.",
        specs=dict(flight_time_min=42, max_range_km=20, weight_kg=1.6, camera="Wide + zoom + thermal + laser"),
        price_usd=None, wiki_title="Autel Robotics", source_url="https://www.autelrobotics.com/",
    ),
    # ------------------------------------------------------------------ Mapping & survey
    dict(
        name="WingtraOne GEN II", manufacturer="Wingtra", category="Mapping & survey",
        description="A vertical take-off fixed-wing drone for survey-grade mapping. It lifts off like a "
                    "helicopter, flies like a plane and covers large areas in one battery.",
        specs=dict(flight_time_min=59, weight_kg=4.5, wingspan_m=1.25, camera="42 MP full-frame mapping"),
        price_usd=None, wiki_title="Wingtra", source_url="https://wingtra.com/mapping-drone-wingtraone/",
    ),
    dict(
        name="Quantum-Systems Trinity F90+", manufacturer="Quantum-Systems", category="Mapping & survey",
        description="A tilt-rotor VTOL mapping drone with long endurance and swappable payloads. "
                    "Aimed at corridor mapping, forestry and large construction sites.",
        specs=dict(flight_time_min=90, wingspan_m=2.4, camera="Swappable mapping payloads"),
        price_usd=None, wiki_title="Quantum-Systems", source_url="https://quantum-systems.com/trinity-f90/",
    ),
    dict(
        name="senseFly eBee X", manufacturer="AgEagle (senseFly)", category="Mapping & survey",
        description="A hand-launched fixed-wing mapping drone with a foam body and a swappable camera. "
                    "Long a standard tool for agriculture, mining and land-survey teams.",
        specs=dict(flight_time_min=90, weight_kg=1.4, wingspan_m=1.16, camera="Swappable (RGB, multispectral, thermal)"),
        price_usd=None, wiki_title="SenseFly eBee", source_url="https://ageagle.com/drones/ebee-x/",
    ),
    # ------------------------------------------------------------------ Agriculture
    dict(
        name="DJI Agras T40", manufacturer="DJI", category="Agriculture",
        description="A coaxial-rotor spraying drone with a 40 L tank and a radar system that follows terrain. "
                    "Also available with a spreading system for seed and granular fertiliser.",
        specs=dict(payload_kg=40, max_speed_kmh=25, notes="40 L spray tank"),
        price_usd=None, wiki_title="DJI Agras", source_url="https://ag.dji.com/t40",
    ),
    dict(
        name="DJI Agras T50", manufacturer="DJI", category="Agriculture",
        description="The next step up in the Agras line, with a larger spreading hopper and a dual-atomising "
                    "spray system. Designed for orchards, paddies and large open fields.",
        specs=dict(payload_kg=40, max_speed_kmh=25, notes="40 L spray tank, 50 L spread hopper"),
        price_usd=None, wiki_title=None, source_url="https://ag.dji.com/t50",
    ),
    # ------------------------------------------------------------------ Delivery & logistics
    dict(
        name="Zipline P1 (Zip)", manufacturer="Zipline", category="Delivery & logistics",
        description="A fixed-wing delivery drone that releases its package by parachute over the drop point. "
                    "Used in long-distance medical-supply delivery networks.",
        specs=dict(payload_kg=1.75, max_range_km=80, wingspan_m=3.0, notes="Round-trip range about 160 km"),
        price_usd=None, wiki_title="Zipline (drone delivery)", source_url="https://www.zipline.com/",
    ),
    dict(
        name="Zipline Platform 2", manufacturer="Zipline", category="Delivery & logistics",
        description="A two-part system: a fixed-wing aircraft that cruises to the area, and a small tethered "
                    "unit that lowers the parcel to the doorstep. Built for quiet, precise home delivery.",
        specs=dict(payload_kg=3.6, max_range_km=16, notes="Service radius about 16 km"),
        price_usd=None, wiki_title=None, source_url="https://www.zipline.com/",
    ),
    # ------------------------------------------------------------------ Long-endurance
    dict(
        name="General Atomics MQ-9 Reaper", manufacturer="General Atomics", category="Long-endurance",
        description="A medium-altitude, long-endurance remotely piloted aircraft used for surveillance and "
                    "reconnaissance. It can stay airborne for more than a day on one fuel load.",
        specs=dict(wingspan_m=20, endurance_h=27, max_speed_kmh=482, ceiling_m=15240, payload_kg=1700),
        price_usd=None, wiki_title="General Atomics MQ-9 Reaper", source_url="https://www.ga-asi.com/remotely-piloted-aircraft/mq-9a",
    ),
    dict(
        name="Northrop Grumman RQ-4 Global Hawk", manufacturer="Northrop Grumman", category="Long-endurance",
        description="A high-altitude, long-endurance surveillance aircraft with a wingspan close to that of a "
                    "small airliner. Flies at altitudes above commercial traffic for more than 30 hours.",
        specs=dict(wingspan_m=39.9, endurance_h=32, max_speed_kmh=575, ceiling_m=18288, payload_kg=1360),
        price_usd=None, wiki_title="Northrop Grumman RQ-4 Global Hawk", source_url="https://www.northropgrumman.com/what-we-do/air/global-hawk",
    ),
    dict(
        name="Baykar Bayraktar TB2", manufacturer="Baykar", category="Long-endurance",
        description="A medium-altitude, long-endurance unmanned aircraft with a pusher propeller and a "
                    "V-shaped tail. Operated from short runways with a ground control station.",
        specs=dict(wingspan_m=12, endurance_h=27, max_speed_kmh=222, ceiling_m=7620, payload_kg=150),
        price_usd=None, wiki_title="Bayraktar TB2", source_url="https://www.baykartech.com/en/uav/bayraktar-tb2/",
    ),
    dict(
        name="Insitu ScanEagle", manufacturer="Insitu (Boeing)", category="Long-endurance",
        description="A small catapult-launched aircraft that is caught in flight by a hanging rope on landing, so it "
                    "needs no runway. Flies day-long surveillance missions from ships and remote sites.",
        specs=dict(wingspan_m=3.11, weight_kg=22, endurance_h=24),
        price_usd=None, wiki_title="Boeing Insitu ScanEagle", source_url="https://www.insitu.com/",
    ),
]

POSTS = [
    dict(
        title="Multirotor or VTOL fixed-wing: which one should map your site?",
        category="Guides", author="Nour Haddad",
        published_at=datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc),
        summary="Coverage per battery, take-off space and image quality pull in different directions. Here is how to weigh them.",
        body="Multirotors win when you need to hover, work in tight spaces or inspect a vertical surface. They take off and land in a few square metres and are easy to learn.\n\n"
             "Fixed-wing VTOL aircraft win on coverage. A single battery can map several hundred hectares, because wings carry the weight instead of rotors. The price is a larger aircraft, a more involved pre-flight routine and a wider landing area.\n\n"
             "A simple rule: under about 40 hectares per day, a multirotor is usually cheaper and quicker overall. Above that, the extra time per flight you save with a VTOL aircraft starts to pay for itself.",
    ),
    dict(
        title="Five battery habits that add months to pack life",
        category="Guides", author="Omar Said",
        published_at=datetime(2026, 10, 15, 9, 0, tzinfo=timezone.utc),
        summary="Most packs fail early because of how they are stored, not how they are flown.",
        body="Store packs at the storage charge level, not full. Leaving them at 100% for days is the quickest way to lose capacity.\n\n"
             "Let a pack cool before you charge it, and let it warm up before a flight in cold weather. Check each cell for swelling after every landing.\n\n"
             "Rotate your packs in a fixed order and log cycles. A pack that sits at the back of the case will age differently from the one you always grab first.",
    ),
    dict(
        title="What a good pre-flight checklist actually covers",
        category="Safety", author="Lina Farouk",
        published_at=datetime(2026, 10, 8, 9, 0, tzinfo=timezone.utc),
        summary="A checklist only helps if it is short enough to use every time. These are the items worth keeping.",
        body="Start with the aircraft: propellers, arms, battery seating and gimbal. Then the link: controller charge, app version and a short range check.\n\n"
             "Then the environment: wind at flight height, people and vehicles in the area, and a planned return point. Write down the return altitude so it clears the tallest obstacle on the route.\n\n"
             "Finish by checking that the return-to-home point was recorded after take-off. It is the one step people skip.",
    ),
    dict(
        title="Remote ID: what operators need to know before the next flight",
        category="Regulation", author="Nour Haddad",
        published_at=datetime(2026, 9, 30, 9, 0, tzinfo=timezone.utc),
        summary="Many regions now expect a drone to broadcast an identifier while it flies. A plain-language overview.",
        body="Remote ID lets authorities and nearby people receive a drone's identifier and position while it is in the air. Rules and deadlines differ by country, so check your own regulator's page before you fly.\n\n"
             "Newer drones often have the broadcast built in. Older ones may need an add-on module. Keep the registration number you receive with the aircraft's paperwork.\n\n"
             "This article is general information, not legal advice. Your national aviation authority is the source for what applies to you.",
    ),
    dict(
        title="Calibrating spray flow before the season starts",
        category="Agriculture", author="Omar Said",
        published_at=datetime(2026, 9, 18, 9, 0, tzinfo=timezone.utc),
        summary="A ten-minute bench test saves a lot of uneven coverage in the field.",
        body="Fill the tank with water and run the pump over a measuring container for one minute at each flow setting. Compare the result to the figure on the screen.\n\n"
             "Do this for every nozzle type you plan to use, because droplet size changes how much liquid reaches the crop. Replace any nozzle that is more than ten percent off.\n\n"
             "Repeat the test whenever you change fluid. Thicker mixtures flow differently from water.",
    ),
    dict(
        title="AeroCorp opens its demo airfield for operator training days",
        category="News", author="AeroCorp Editorial",
        published_at=datetime(2026, 9, 5, 9, 0, tzinfo=timezone.utc),
        summary="Monthly hands-on sessions for inspection, mapping and agriculture teams.",
        body="Starting this month, our demo airfield hosts one training day per month. Each session covers one use case: inspection, mapping or agriculture.\n\n"
             "Teams bring their own questions and fly the aircraft they are considering. Instructors are on hand for flight planning and data processing.\n\n"
             "Use the contact page to ask for the next date for your team.",
    ),
]

