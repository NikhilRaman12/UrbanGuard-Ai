import random
from .models import TelemetryIn
SECTORS=[("MUC-ALT-01","Altstadt-Lehel",48.137,11.576,"drainage"),("MUC-SCH-02","Schwabing",48.166,11.586,"water_body"),("MUC-GIE-03","Giesing",48.115,11.596,"waste"),("MUC-BOG-04","Bogenhausen",48.154,11.633,"weather"),("MUC-NEU-05","Neuhausen",48.155,11.531,"citizen_report")]
def readings():
    result=[]
    for i,(sid,d,lat,lng,source) in enumerate(SECTORS):
        critical = i == random.randrange(5)
        result.append(TelemetryIn(sector_id=sid,district=d,latitude=lat,longitude=lng,source=source,temperature_c=random.uniform(20,31),standing_water_hours=random.uniform(42,130) if critical else random.uniform(0,28),organic_waste_pct=random.uniform(55,95) if critical else random.uniform(5,50),sewer_level_pct=random.uniform(75,98) if critical else random.uniform(25,75),ph=random.uniform(6.2,8.2),clog_probability=random.uniform(60,95) if critical else random.uniform(5,55),report_summary="Standing water reported near public access." if source=="citizen_report" else None))
    return result
