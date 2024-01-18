from dash.dependencies import Input, Output
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from mpl_toolkits.mplot3d import Axes3D
import plotly.graph_objects as go
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from datetime import timedelta
import random, yfinance as yf
from datetime import datetime
import numpy as np
from createTool import empColours

signalLookback, signalBlock, trail1, factor1 = 10, timedelta(days=5), 21, 2
triggerPrice, tradePrice = 'Close', 'Open'
endDate, startDate = datetime.now(), datetime.now() - timedelta(days=60)

# DEFINE TICKER UNIVERSE
dachTickerDict = {
    "1&1": "1U1.DE", "2G Energy": "2GB.DE", "3U": "UUU.DE", "7C Solarparken": "HRPK.DE", "ÖKOWORLD (ex Versiko)": "VVV3.DE",
    "Österreichische Post": "POST.VI", "ABB (Asea Brown Boveri)": "ABBN.SW", "ABO Wind": "AB9.DE", "Adecco SA": "ADEN.SW",
    "adesso": "ADN1.DE", "adidas": "ADS.DE", "Adler Real Estate": "ADL.DE", "ADM Hamburg": "OEL.SG", "ADVA Optical Networking": "ADV.DE",
    "Adval Tech": "ADVN.SW", "AGRANA": "AGR.VI", "AIXTRON": "AIXA.DE", "ALBA": "ABA.SG", "Alcon": "ALC.SW",
    "All for One Group": "A1OS.DE", "Allane": "LNSX.DE", "Allgeier": "AEIN.DE", "ALSO": "ALSN.SW", "AlzChem Group": "ACT.DE",
    "Amadeus FiRe": "AAD.DE", "AMAG": "AMAG.VI", "Andritz": "ANDR.VI", "Arbonia": "ARBN.SW", "artnet": "ART.DE",
    "ARYZTA": "ARYN.SW", "Ascom": "ASCN.SW", "AT S (AT&S)": "ATS.VI", "ATOSS Software": "AOF.DE", "Aumann": "AAG.DE",
    "AURELIUS": "AR4.DE", "Aurubis": "NDA.DE", "AUTO1": "AG1.DE", "Aves One": "AVES.DE", "Barry Callebaut": "BARN.SW",
    "BASF": "BAS.DE", "Basler": "BSL.DE", "BAUER": "B5A.DE", "BAVARIA Industries Group": "B8A.DE", "Bayer": "BAYN.DE",
    "BayWa": "BYW6.DE", "Bechtle": "BC8.DE", "Befesa": "BFSA.DE", "Beiersdorf": "BEI.DE", "BELIMO": "BEAN.SW",
    "Bell": "BELL.SW", "Berentzen-Gruppe": "BEZ.DE", "Bertrandt": "BDT.DE", "Beta Systems Software": "BSS.SG", "bet-at-home.com": "ACX.DE",
    "Bijou Brigitte": "BIJ.DE", "Bilfinger": "GBF.DE", "Binect": "MA10.DE", "Biofrontera": "B8F.DE", "Biotest vz.": "BIO3.DE",
    "Bitcoin Group": "ADE.DE", "BKW": "BKW.SW", "Blue Cap": "B7E.DE", "BMW": "BMW.DE", "Bossard": "BOSN.SW",
    "BRAIN Biotech": "BNN.DE", "Brenntag": "BNR.DE", "Brockhaus Technologies": "BKHT.DE", "Bucher Industries": "BUCN.SW",
    "Burckhardt Compression": "BCHN.SW", "Burgenland": "BHD.VI", "Burkhalter": "BRKN.SW", "BVB (Borussia Dortmund)": "BVB.DE",
    "Bystronic (ex Conzzeta)": "BYS.SW", "CA Immobilien": "CAI.VI", "Calida": "CALN.SW", "CANCOM": "COK.DE",
    "capsensixx": "CPX.DE", "Carl Zeiss Meditec": "AFX.DE", "Ceconomy St.": "CEC.DE", "CENIT": "CSH.DE", "CEWE Stiftung": "CWC.DE",
    "CHERRY": "C3RY.DE", "Cicor Technologies": "CICN.SW", "Clariant": "CLN.SW", "clearvise": "ABO.DE", "CLIQ Digital": "CLIQ.DE",
    "COLTENE": "CLTN.SW", "Comet": "COTN.SW", "Compleo Charging Solutions": "C0M.DE", "CompuGroup Medical": "COP.DE",
    "Continental": "CON.DE", "Covestro": "1COV.DE", "CropEnergies": "CE2.DE", "CTS Eventim": "EVD.DE", "Cyan": "CYR.DE",
    "Dürr": "DUE.DE", "Daldrup Söhne (Daldrup)": "4DS.DE", "DATA MODUL": "DAM.DE", "DATAGROUP": "D6H.DE", "Datron": "DAR.DE",
    "DEFAMA Deutsche Fachmarkt": "DEF.DE", "Delignit": "DLX.DE", "Delivery Hero": "DHER.DE", "Delticom": "DEX.DE",
    "Dermapharm": "DMP.DE", "Deutsche Börse": "DB1.DE", "Deutsche Beteiligungs": "DBAN.DE", "Deutsche Euroshop": "DEQ.DE",
    "Deutsche Konsum REIT-AG": "DKG.DE", "Deutsche Post": "DPW.DE", "Deutsche Rohstoff": "DR0.DE", "Deutsche Telekom": "DTE.DE",
    "Deutsche Wohnen": "DWNI.DE", "DEUTZ": "DEZ.DE", "DIC Asset": "DIC.DE", "DKSH": "DKSH.SW", "DMG MORI": "GIL.DE",
    "DO": "DOC.VI", "DocCheck": "AJ91.DE", "dormakaba": "DOKA.SW", "DOTTIKON ES": "DESN.SW", "Dr. Hönle": "HNL.DE",
    "Drägerwerk": "DRW3.DE", "Dufry": "DUFN.SW", "E.ON": "EOAN.DE", "EASY Software": "ESY.DE", "Eckert Ziegler Strahlen- und Medizintechnik": "EUZ.DE",
    "ecotel communication": "E4C.DE", "edel": "EDL.DE", "Edisun Power Europe": "ESUN.SW", "Einhell Germany": "EIN3.DE",
    "Elmos Semiconductor": "ELG.DE", "ElringKlinger": "ZIL2.DE", "elumeo": "ELB.DE", "Emmi": "EMMN.SW", "EMS-CHEMIE": "EMSN.SW",
    "EnBW": "EBK.DE", "ENCAVIS": "ECV.DE", "Endor": "E2N.SG", "Energiedienst": "EDHN.SW", "Energiekontor": "EKT.DE",
    "EnviTec Biogas": "ETG.DE", "EQS Group": "EQS.DE", "Ernst Russ": "HXCK.DE", "EUROKAI vz.": "EUK3.SG", "EVN": "EVN.VI",
    "Evonik": "EVK.DE", "EVOTEC": "EVT.DE", "Exasol": "EXL.DE", "Fabasoft": "FAB.DE", "FACC": "FACC.VI",
    "fashionette": "FSNT.DE", "Fielmann": "FIE.DE", "FinLab": "A7A.DE", "First Sensor": "SIS.DE", "flatexDEGIRO": "FTK.DE",
    "Flughafen Wien": "FLU.VI", "Flughafen Zürich": "FHZN.SW", "Forbo International": "FORN.SW", "Formycon": "FYB.DE",
    "FORTEC Elektronik": "FEV.DE", "Francotyp-Postalia": "FPH.DE", "Fraport": "FRA.DE", "freenet": "FNTN.DE",
    "Frequentis": "FQT.VI", "Fresenius Medical Care": "FME.DE", "FRIWO": "CEA.DE", "FRoSTA": "NLM.SG", "Funkwerk": "FEW.SG",
    "Galenica": "GALE.SW", "Garmin": "GRMN.SW", "Gateway Real Estate": "GTY.DE", "GEA": "G1A.DE", "Geberit": "GEBN.SW",
    "GELSENWASSER": "WWG.SG", "Geratherm Medical": "GME.DE", "Gerresheimer": "GXI.DE", "Gesco": "GSC1.DE", "GFT": "GFT.DE",
    "Gigaset": "GGS.DE", "Givaudan": "GIVN.SW", "GK SOFTWARE": "GKS.DE", "Grammer": "GMM.DE", "Grand City Properties": "GYC.DE",
    "GRENKE": "GLJ.DE", "GSW Immobilien": "GIB.SG", "HAEMATO": "HAEK.DE", "HanseYachts": "H9Y.DE", "Hapag-Lloyd": "HLAG.DE",
    "HAWESKO": "HAW.DE", "HBM Healthcare Investments": "HBMN.SW", "Heidelberg Pharma": "HPHA.DE", "HeidelbergCement": "HEI.DE",
    "Heidelberger Druckmaschinen": "HDD.DE", "Heliad Equity Partners": "HPBK.DE", "HELLA": "HLE.DE", "HelloFresh": "HFG.DE",
    "HELMA": "H5E.DE", "Henkel vz.": "HEN3.DE", "HENSOLDT": "HAG.DE",
    "Hermle": "MBH3.SG", "HHLA": "HHFA.DE", "HOCHTIEF": "HOT.DE", "Homag": "HG1.SG", "Home24": "H24.DE",
    "HORNBACH Baumarkt": "HBM.DE", "Huber + Suhner": "HUBN.SW", "HUGO BOSS": "BOSS.DE", "Hypoport": "HYQ.DE", "Hyrican": "HYI.SG",
    "IBU-tec": "IBU.DE", "IFA Hotel Touristik": "IFA.DE", "InCity Immobilien": "IC8.DE", "INDUS": "INH.DE", "Inficon": "IFCN.SW",
    "Infineon": "IFX.DE", "init innovation in traffic systems": "IXX.DE", "InnoTec": "TSS.SG", "Instone Real Estate Group": "INS.DE",
    "INTERROLL": "INRN.SW", "INTERSHOP Communications": "ISHA.DE", "InTiCa Systems": "IS7.DE", "InVision": "IVX.DE", "IVF HARTMANN": "VBSN.SW",
    "IVU Traffic": "IVU.DE", "JDC Group": "JDC.DE", "JENOPTIK": "JEN.DE", "JOST Werke": "JST.DE", "Jungheinrich": "JUN3.DE",
    "K+S": "SDF.DE", "Kühne + Nagel International": "KNIN.SW", "Kapsch TrafficCom": "KTCG.VI", "KATEK": "KTEK.DE", "KHD Humboldt Wedag International": "KWG.DE",
    "KION GROUP": "KGX.DE", "Klöckner": "KCO.DE", "Knaus Tabbert": "KTA.DE", "Knorr-Bremse": "KBX.DE", "Koenig Bauer": "SKB.DE",
    "Kontron": "KTN.VI", "KPS": "KSC.DE", "KRONES": "KRN.DE", "KSB": "KSB.DE", "Kudelski": "KUD.SW",
    "Kulmbacher Brauerei": "KUL.MU", "KWS SAAT": "KWS.DE", "Landis+Gyr (Landis Gyr)": "LAND.SW", "LANXESS": "LXS.DE", "Lechwerke": "LEC.SG",
    "Leclanche (Leclanché SA)": "LECN.SW", "LEG Immobilien": "LEG.DE", "LEIFHEIT": "LEI.DE", "LEM": "LEHN.SW", "Lenzing": "LNZ.VI",
    "Lindt": "LISP.SW", "Logitech": "LOGN.SW", "Lonza": "LONN.SW", "LPKF Laser Electronics": "LPK.DE", "LS telcom": "LSX.DE",
    "Ludwig Beck am Rathauseck - Textilhaus Feldmeier": "ECK.DE", "Lufthansa": "LHA.DE", "Mühlbauer": "MUB.DE", "Müller - Die lila Logistik": "MLL.DE",
    "Manz": "M5Z.DE", "Masterflex": "MZX.DE", "MAX Automation": "MXHN.DE", "Mayr-Melnhof Karton": "MMK.VI", "MBB": "MBB.DE",
    "Medacta": "MOVE.SW", "MediClin": "MED.DE", "Medigene": "MDG1.DE", "MEDION": "MDN.DE", "Medios": "ILM1.DE",
    "Meier Tobler": "MTG.SW", "Mensch und Maschine Software": "MUM.DE", "Mercedes-Benz Group (ex Daimler)": "MBG.DE", "Merck": "MRK.DE", "METALL ZUG": "METN.SW",
    "METRO vz.": "B4B3.DE", "MeVis Medical Solutions": "M3V.DE", "Meyer Burger": "MBTN.SW", "Mister Spex": "MRX.DE", "mobilezone": "MOZN.SW",
    "Mobimo": "MOBN.SW", "MOBOTIX": "MBQ.DE", "MorphoSys": "MOR.DE", "MPC Münchmeyer Petersen Capital": "MPCK.DE", "MPH Health Care": "93M1.DE",
    "MS Industrie": "MSAG.DE", "MTU Aero Engines": "MTX.DE", "Muehlhan": "M4N.DE", "Mutares": "MUX.DE", "MVV Energie": "MVV1.DE",
    "Nabaltec": "NTG.DE", "Nagarro": "NA9.DE", "Nemetschek": "NEM.DE", "New Work": "NWO.DE", "NEXUS": "NXU.DE",
    "NFON": "NFN.DE", "Nordex": "NDX1.DE", "NORMA Group": "NOEJ.DE", "Northern Data": "NB2.DE", "Novartis": "NOVN.SW",
    "Nynomic": "M7U.DE", "OHB": "OHB.DE", "OMV": "OMV.VI", "ORBIS": "OBS.DE", "Orior": "ORON.SW",
    "OSRAM": "OSR.SG", "Ottakringer Brauerei": "OTS.VI", "OVB": "O4B.DE", "Palfinger": "PAL.VI", "Pantaflix": "PAL.DE",
    "paragon": "PGN.DE", "PATRIZIA": "PAT.DE", "PAUL HARTMANN": "PHH2.SG", "Pfeiffer Vacuum": "PFV.DE", "Pferdewetten.de": "EMH.DE",
    "PharmaSGP": "PSG.DE", "Pierer Mobility (ex KTM Industries)": "PMAG.DE", "Pilkington Deutschland": "FDD.F", "PLAZZA": "PLAN.SW", "PNE": "PNE3.DE",
    "Polytec": "PYT.VI", "PORR": "POS.VI", "Porsche Automobil vz.": "PAH3.DE", "Progress-Werk Oberkirch": "PWO.DE", "ProSiebenSat.1 Media": "PSM.DE",
    "PSI Software": "PSAN.DE", "publity": "PBY.DE", "PUMA": "PUM.DE", "PVA TePla": "TPE.DE", "q.beyond (ex QSC)": "QBY.DE",
    "QIAGEN": "QIA.DE", "R. Stahl": "RSL2.DE", "RATIONAL": "RAA.DE", "RHÖN-KLINIKUM": "RHK.DE", "Rheinmetall": "RHM.DE",
    "Ringmetall": "HP3A.DE", "Roche": "ROG.SW", "Rosenbauer": "ROS.VI", "RTL": "RRTL.DE", "RWE": "RWE.DE",
    "SÜSS MicroTec": "SMHN.DE", "Südwestdeutsche Salzwerke": "SSH.SG", "Südzucker": "SZU.DE", "Salzgitter": "SZG.DE", "SAP": "SAP.DE",
    "Sartorius vz.": "SRT3.DE", "Schaeffler": "SHA.DE", "Schaltbau": "SLT.DE", "Scherzer": "PZS.DE", "Schindler": "SCHP.SW",
    "Schloss Wachenheim": "SWA.DE", "Schoeller-Bleckmann": "SBO.VI", "Schweizer Electronic": "SCE.DE", "Scout24": "G24.DE", "secunet Security Networks": "YSN.DE",
    "Semperit": "SEM.VI", "Sensirion": "SENS.SW", "Serviceware": "SJJ.DE", "SFC Energy": "F3C.DE", "SFS": "SFSN.SW",
    "SGL Carbon": "SGL.DE", "SGS SA": "SGSN.SW", "Redcare Pharmacy": "RCR.DE", "Siegfried": "SFZN.SW", "Siemens": "SIE.DE",
    "Siemens Energy": "ENR.DE", "Siemens Healthineers": "SHL.DE", "SIG Combibloc": "SIGN.SW", "Sika": "SIKA.SW", "Siltronic": "WAF.DE",
    "Singulus Technologies": "SNG.DE", "sino": "XTP.DE", "Sixt": "SIX2.DE", "SLM Solutions": "AM3D.SG", "SMA Solar": "S92.DE",
    "SNP Schneider-Neureither Partner": "SHF.DE", "Softing": "SYT.DE", "Software": "SOW.DE", "SoftwareONE": "SWON.SW", "Sonova": "SOON.SW",
    "Stadler Rail": "SRAIL.SW", "STEICO": "ST5.DE", "STEMMER IMAGING": "S9I.DE", "STO": "STO3.DE", "Ströer": "SAX.DE",
    "STRABAG": "STR.VI", "STRATEC": "SBS.DE", "STS Group": "SF3.DE", "SURTECO GROUP": "SUR.DE", "SUSE": "SUSE.DE",
    "Swatch (N)": "UHRN.SW", "Swiss Prime Site": "SPSN.SW", "Swisscom": "SCMN.SW", "Symrise": "SY1.DE", "syzygy": "SYZ.DE",
    "TAG Immobilien": "TEG.DE", "TAKKT": "TTK.DE", "Talanx": "TLX.DE", "TeamViewer": "TMV.DE", "Tecan (N)": "TECN.SW",
    "technotrans": "TTR1.DE", "Tele Columbus": "TC1.HM", "Telekom Austria": "TKA.VI", "Temenos": "TEMN.SW", "The Social Chain": "PU11.DE",
    "thyssenkrupp": "TKA.DE", "TLG IMMOBILIEN": "TLG.HM", "TRATON": "8TRA.DE", "UMT United Mobility Technology": "UMDK.DE", "Uniper": "UN01.DE",
    "United Internet": "UTDI.DE", "USU Software": "OSP2.DE", "UZIN UTZ": "UZU.DE", "Vantage Towers": "VTWR.DE", "va-Q-tec": "VQT.DE",
    "Varta": "VAR1.DE", "VAT": "VACN.SW", "Vectron Systems": "V3S.DE", "VERBIO Vereinigte BioEnergie": "VBK.DE", "Verbund": "VER.VI",
    "Vetropack A": "VETN.SW", "Villeroy Boch": "VIB3.DE", "Viscom": "V6C.DE", "Vita 34": "V3V.DE", "voestalpine": "VOE.VI",
    "Volkswagen (VW) vz.": "VOW3.DE", "Voltabox": "VBX.DE", "Vonovia": "VNA.DE", "Vossloh": "VOS.DE",
    "Wüstenrot Württembergische": "WUW.DE", "WACKER CHEMIE": "WCH.DE", "Wacker Neuson": "WAC.DE", "WashTec": "WSU.DE", "Westwing": "WEW.DE",
    "Wienerberger": "WIE.VI", "Wolftank-Adisa": "WOLF.VI", "YOC": "YOC.DE", "Ypsomed": "YPSN.SW", "Zalando": "ZAL.DE", "ZEAL Network": "TIMA.DE", 
    "Zehnder A": "ZEHN.SW", "zooplus": "ZO1.DE", "ZUMTOBEL": "ZAG.VI", "u-blox": "UBXN.SW", "Vitesco Technologies": "VTSC.DE", "IONOS": "IOS.DE"}
sdaxTickerDict = {stock_name: ticker for stock_name, ticker in dachTickerDict.items() if stock_name in [
    "1&1 AG", "adesso SE", "ADTRAN Holdings Inc.", "Adtran Networks SE", "AMADEUS FIRE AG", "Aroundtown Property Hldgs S.A.",
    "Atoss Software AG", "AUTO1 Group SE", "BayWa AG vink. Namens-Aktien", "Bilfinger SE", "Borussia Dortmund GmbH&Co.KGaA",
    "CANCOM SE", "CECONOMY AG", "CEWE Stiftung & Co. KGaA", "CompuGroup Medical SE & Co.KGaA", "Dermapharm Holding SE",
    "Deutsche Beteiligungs AG", "Deutsche Pfandbriefbank AG", "Deutsche Wohnen SE", "DEUTZ AG", "Drägerwerk AG & Co. KGaA VZ",
    "DWS Group GmbH & Co. KGaA", "Eckert & Ziegler Str.-u.Med.AG", "Elmos Semiconductor SE", "Energiekontor AG", "Fielmann Group AG",
    "flatexDEGIRO AG", "GFT Technologies SE", "Grand City Properties S.A.", "GRENKE AG", "HAMBORNER REIT AG", "Heidelberger Druckmaschinen AG",
    "Hornbach Holding AG&Co.KGaA", "Hypoport SE", "INDUS Holding AG", "IONOS Group SE", "JOST Werke SE", "Klöckner & Co SE",
    "Kontron AG", "KRONES AG", "KWS SAAT SE & Co. KGaA", "METRO AG", "MorphoSys AG", "Nagarro SE", "New Work SE", "NORMA Group SE",
    "PATRIZIA SE", "Pfeiffer Vacuum Technology AG", "PNE AG", "PVA TePla AG", "SAF HOLLAND SE", "Salzgitter AG", "Schaeffler AG VZ",
    "secunet Security Networks AG", "SFC Energy AG", "SGL CARBON SE", "Siltronic AG", "Sto SE & Co. KGaA", "STRATEC SE", "Südzucker AG",
    "SYNLAB AG", "SÜSS MicroTec SE", "thyssenkrupp nucera AG&Co.KGaA", "TRATON SE", "VARTA AG", "VERBIO Vereinigt.BioEnergie AG",
    "Vossloh AG", "Wacker Neuson SE", "Wüstenrot& Württembergische AG", "Zeal Network SE"]}
aiTickerDict = {
    "NVIDIA Corporation": "NVDA",
    "Alphabet Inc. (Google)": "GOOGL",
    "Microsoft Corporation": "MSFT",
    "International Business Machines Corporation (IBM)": "IBM",
    "Amazon.com, Inc.": "AMZN",
    "Meta Platforms, Inc.": "META",
    "Salesforce.com, Inc.": "CRM",
    "Intel Corporation": "INTC",
    "Advanced Micro Devices, Inc.": "AMD",
    "Baidu, Inc.": "BIDU",
    "Tencent Holdings Limited": "0700.HK",
    "Alibaba Group Holding Limited": "BABA",
    "SAP SE": "SAP",
    "Oracle Corporation": "ORCL",
    "Siemens AG": "SIE.DE",
    "ABB Ltd": "ABB",
    "Honeywell International Inc.": "HON",
    "Qualcomm Incorporated": "QCOM",
    "Splunk Inc.": "SPLK",
    "Palantir Technologies Inc.": "PLTR",
    "C3.ai, Inc.": "AI",
    "UiPath Inc.": "PATH",
    "Teradata Corporation": "TDC",
    "Micron Technology, Inc.": "MU",
    "Snowflake Inc.": "SNOW",
    "Twilio Inc.": "TWLO",
    "DocuSign, Inc.": "DOCU",
    "Zoom Video Communications, Inc.": "ZM",
    "Roblox Corporation": "RBLX",
    "Autodesk, Inc.": "ADSK",
    "Tesla, Inc.": "TSLA",
    "NICE Ltd.": "NICE",
    "Zebra Technologies Corporation": "ZBRA",
    "Xilinx, Inc.": "XLNX",
    "CrowdStrike Holdings, Inc.": "CRWD",
    "Zscaler, Inc.": "ZS",
    "ServiceNow, Inc.": "NOW",
    "Workday, Inc.": "WDAY"}
noTicker = [
    "Fabasoft", "Garmin", "Pierer Mobility (ex KTM Industries)",
    "QIAGEN", "Redcare Pharmacy", "Siemens Energy", "SAF-HOLLAND", "Deufol", "Wild Bunch", "Limes Schlosskliniken",
    "centrotherm international", "M1 Kliniken", "FUCHS PETROLUB", "CHAPTERS Group", "Zapf Creation", "Pulsion Medical Systems", "Implenia"]
dataPoints = ['beta', 'trailingPE', 'marketCap', 'fiftyTwoWeekLow', 'fiftyTwoWeekHigh',
    'fiftyDayAverage', 'twoHundredDayAverage', 'currency', 'enterpriseValue',
    'profitMargins', 'floatShares', 'sharesOutstanding', 'sharesShort', 'bookValue',
    'priceToBook', 'currentPrice', 'targetHighPrice', 'targetLowPrice', 'targetMeanPrice',
    'totalCash', 'debtToEquity', 'returnOnAssets', 'returnOnEquity', 'grossProfits',
    'freeCashflow', 'operatingCashflow', 'earningsGrowth', 'revenueGrowth',
    'grossMargins', 'ebitdaMargins', 'operatingMargins']
selectedDataPoints = ['beta', 'trailingPE', 'marketCap', 'fiftyTwoWeekLow', 'fiftyTwoWeekHigh']

# SELECT TICKER UNIVERSE
selectedTickers = list(dachTickerDict.items())[:55]
tradeSignals = []

# MAIN
sampledTickers = [ticker for _, ticker in selectedTickers]
for stockName, ticker in dachTickerDict.items():
    if ticker in sampledTickers:
        try:
            df = yf.download(ticker, start=startDate, end=endDate)
            if not df.empty:
                df['volume' + str(trail1)] = df['Volume'].rolling(window=trail1).mean().round(0)
                df['lowerBB'] = (df['Close'].rolling(window=trail1).mean() - (df['Close'].rolling(window=trail1).std() * factor1)).round(2)
                for i in range(1, signalLookback + 1):
                    if (df['Low'].iloc[-i] < df['lowerBB'].shift(1).iloc[-i]) and (df['Volume'].iloc[-i] > (df['volume' + str(trail1)].shift(1).iloc[-i] * factor1)):
                        tradeSignals.append((stockName, df.index[-i]))
        except Exception as e:
            print(f"Error downloading data for {stockName} ({ticker}): {e}")

# CLEAN OUT CONSECUTIVE SIGNALS
cleanedTradeSignals = []
seenTickers = {}
for stockName, signalDate in tradeSignals:
    if stockName not in seenTickers or signalDate - seenTickers[stockName] > signalBlock:
        seenTickers[stockName] = signalDate
        cleanedTradeSignals.append((stockName, signalDate))
tradeSignals = cleanedTradeSignals

# GET YFINANCE DATA FOR SIGNAL TICKER
tradeSignalsData = {s[0]: {'price': yf.download(dachTickerDict[s[0]], start=startDate, end=endDate)} for s in tradeSignals}
for s in tradeSignals:
    ticker = dachTickerDict[s[0]]
    tradeSignalsData[s[0]]['info'] = yf.Ticker(ticker).info

# BACKTEST
if "backtest" == "backtest":
    tradePerformance = {}
    for stockName, signalDate in tradeSignals:
        df = tradeSignalsData[stockName]['price']
        nextDayIndex = df.index[df.index > signalDate]
        if not nextDayIndex.empty:
            nextDayOpen = df.loc[nextDayIndex[0], 'Open']
            mostRecentClose = df['Close'].iloc[-1]
            if stockName not in tradePerformance:
                tradePerformance[stockName] = []
            if nextDayOpen != 0:
                performance = (mostRecentClose - nextDayOpen) / nextDayOpen
                tradePerformance[stockName].append({'date': signalDate, 'performance': performance})

    # PLOT BACKTEST
    dates = [mdates.date2num(performance['date']) for _, performances in tradePerformance.items() for performance in performances]
    performances = [performance['performance'] * 100 for _, performances in tradePerformance.items() for performance in performances]
    tickerNames = [stockName for stockName, _ in tradeSignals for _ in tradePerformance.get(stockName, [])]
    uniqueTickers = sorted(set(tickerNames))
    tickerToNum = {ticker: i for i, ticker in enumerate(uniqueTickers, start=1)}
    tickerNums = [tickerToNum[ticker] for ticker in tickerNames]
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')
    colorMap = plt.colormaps['viridis']
    normPerformances = plt.Normalize(min(performances), max(performances))
    scatter = ax.scatter(dates, tickerNums, performances, c=performances, cmap=colorMap, marker='o', norm=normPerformances)
    ax.xaxis.line.set_color((0.5, 0.5, 0.5, 0.7))
    ax.yaxis.line.set_color((0.5, 0.5, 1.0, 0.7))
    ax.zaxis.line.set_color((0.6, 0.0, 0.6, 0.7)) 
    ax.set_zlabel('Performance (%)')
    ax.set_title('Empirica Investment - Trade Signal Analysis')
    ax.xaxis.set_major_locator(plt.MaxNLocator(10))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda num, _: mdates.num2date(num).strftime('%Y-%m-%d')))
    ax.yaxis.set_ticks(range(1, len(uniqueTickers) + 1))
    ax.yaxis.set_ticklabels(uniqueTickers)
    for i in range(len(dates)):
        ax.text(dates[i], tickerNums[i], performances[i], tickerNames[i], size=10, zorder=1, color='k')
    plt.show()

# DASHBOARD
if "dashboard" == "dashboar":
    numRows = len(tradeSignalsData)
    subplotTitles = [item for sublist in zip(list(tradeSignalsData.keys())[:numRows], [None] * numRows) for item in sublist]
    fig = make_subplots(
        rows=numRows, cols=2, column_widths=[0.7, 0.3], shared_xaxes=True, vertical_spacing=0.1, 
        subplot_titles=subplotTitles, specs=[[{"type": "xy", "secondary_y": True}, {"type": "table"}] for _ in range(numRows)])
    for i, (stockName, data) in enumerate(list(tradeSignalsData.items())[:numRows]):
        df = data['price']
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name=f'{stockName} Close', line=dict(color='navy', width=2)), row=i+1, col=1, secondary_y=False)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name=f'{stockName} Volume', marker=dict(color='lightgrey'), opacity=0.4), row=i+1, col=1, secondary_y=True)
        tableHeaders = ['Metric', 'Value']
        tableData = [[dp for dp in selectedDataPoints], [data['info'][dp] if dp in data['info'] else 'N/A' for dp in selectedDataPoints]]
        fig.add_trace(go.Table(
            header=dict(values=tableHeaders, fill_color='paleturquoise', align='center', font=dict(color='black', size=12)),
            cells=dict(values=tableData, fill_color='lavender', align='left', font=dict(color='darkslategray', size=11))), row=i+1, col=2)
    fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', font_color='navy', title_x=0.5, height=300*numRows, showlegend=False)
    fig.update_xaxes(showline=True, linewidth=2, linecolor='grey', mirror=True, gridcolor='lightgrey')
    fig.update_yaxes(showline=True, linewidth=2, linecolor='grey', mirror=True, title_text="Price", secondary_y=False)
    fig.update_yaxes(title_text="Volume", secondary_y=True)
    fig.show()
