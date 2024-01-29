### pipes, htf, cwh, livBol, vcp, 21d200d

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
import pandas as pd

signalLookback, signalBlock, trail1, trail2, factor1 = 90, timedelta(days=0), 15, 50, 2
triggerPrice, tradePrice = 'Close', 'Open'
endDate, startDate = datetime.now(), datetime.now() - timedelta(days=150)
tradeSignalsTickerDate, cleanedTradeSignals, seenTickers = [], [], {}

# TICKER UNIVERSE
dachTickerDict = {
    "1&1": "1U1.DE", "2G Energy": "2GB.DE", "3U": "UUU.DE", "7C Solarparken": "HRPK.DE", "ÖKOWORLD (ex Versiko)": "VVV3.DE",
    "Österreichische Post": "POST.VI", "ABB (Asea Brown Boveri)": "ABBN.SW", "ABO Wind": "AB9.DE", "Adecco SA": "ADEN.SW",
    "adesso": "ADN1.DE", "adidas": "ADS.DE", "Adler Real Estate": "ADJ.DE", "ADM Hamburg": "OEL.SG", "ADVA Optical Networking": "ADV.DE",
    "Adval Tech": "ADVN.SW", "AGRANA": "AGR.VI", "AIXTRON": "AIXA.DE", "ALBA": "ABA.SG", "Alcon": "ALC.SW",
    "All for One Group": "A1OS.DE", "Allane": "LNSX.DE", "Allgeier": "AEIN.DE", "ALSO": "ALSN.SW", "AlzChem Group": "ACT.DE",
    "Amadeus FiRe": "AAD.DE", "AMAG": "AMAG.VI", "Andritz": "ANDR.VI", "Arbonia": "ARBN.SW", "artnet": "ART.DE",
    "ARYZTA": "ARYN.SW", "Ascom": "ASCN.SW", "AT S (AT&S)": "ATS.VI", "ATOSS Software": "AOF.DE", "Aumann": "AAG.DE",
    "AURELIUS": "AR4.DE", "Aurubis": "NDA.DE", "AUTO1": "AG1.DE", "Barry Callebaut": "BARN.SW",
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
    "Zehnder A": "ZEHN.SW", "zooplus": "ZO1.DE", "ZUMTOBEL": "ZAG.VI", "u-blox": "UBXN.SW", "Vitesco Technologies": "VTSC.DE", "IONOS": "IOS.DE",
    "Fabasoft": "FAA.DE", "Garmin": "GRMN", "Pierer Mobility (ex KTM Industries)": "PKTM.VI",
    "QIAGEN":"QGEN", "Redcare Pharmacy":"RDC.DE", "Siemens Energy":"ENR.DE", "SAF-HOLLAND":"SFQ.DE", "Deufol":"DE1.HM", 
    "M1 Kliniken": "M12.DE", "FUCHS PETROLUB": "FPE3.DU", "Zapf Creation": "ZPF.HM"}
selectedTickers = list(dachTickerDict.items())[:50]
sampledTickers = [ticker for _, ticker in selectedTickers]
selectedDataPoints = ['fiftyTwoWeekHigh', 'fiftyDayAverage', 'twoHundredDayAverage']

# PATTERN TEST
def indicatorStorage():
    df['volume' + str(trail1)] = df['Volume'].rolling(window=trail1).mean().round(1)
    df['volume' + str(trail2)] = df['Volume'].rolling(window=trail2).mean().round(1)
    df['tr'] = pd.concat([df['High'] - df['Low'], (df['High'] - df[triggerPrice]).abs(), (df['Low'] - df[triggerPrice]).abs()], axis=1).max(axis=1)
    df['atr' + str(trail1)] = df['tr'].rolling(window=trail1).mean()
    df['atr' + str(trail2)] = df['tr'].rolling(window=trail2).mean()
    df['ema' + str(trail1)] = df[triggerPrice].ewm(span=trail1).mean()
    df['ema' + str(trail2)] = df[triggerPrice].ewm(span=trail2).mean()
    df['er' + str(trail1)] = df[triggerPrice].diff(trail1).abs() / df[triggerPrice].diff().abs().rolling(window=trail1).sum()
    df['er' + str(trail2)] = df[triggerPrice].diff(trail2).abs() / df[triggerPrice].diff().abs().rolling(window=trail2).sum()
    df['upperBb'] = df['Close'].rolling(window=trail1).mean() + (df['Close'].rolling(window=trail1).std() * factor1)
    df['lowerBb'] = df['Close'].rolling(window=trail1).mean() - (df['Close'].rolling(window=trail1).std() * factor1)
    df['macd' + str(trail1) + '-' + str(trail2)] = df['ema' + str(trail1)] / df['ema' + str(trail2)] - 1
    df['noise' + str(trail1) + '-' + str(trail2)] = np.log((df['er' + str(trail1)] + 1e-6) / (df['er' + str(trail2)] + 1e-6))
    df['volumedriven' + str(trail1) + '-' + str(trail2)] = (df['volume' + str(trail1)] / df['volume' + str(trail2)]) / df['er' + str(trail1)].rolling(window=trail1).mean()
def livermoreReversal():
    df['volume' + str(trail1)] = df['Volume'].rolling(window=trail1).mean().round(0)
    df['lowerBB'] = (df['Close'].rolling(window=trail1).mean() - (df['Close'].rolling(window=trail1).std() * factor1)).round(2)
    for i in range(1, signalLookback + 1):
        if (df['Low'].iloc[i] < df['lowerBB'].shift(1).iloc[i]) and (df['Volume'].iloc[i] > (df['volume' + str(trail1)].shift(1).iloc[i] * factor1)):
            tradeSignalsTickerDate.append((stockName, df.index[i]))
def miniVcp():
    df['volume' + str(trail1)] = df['Volume'].rolling(window=trail1).mean().round(1)
    df['volume' + str(trail2)] = df['Volume'].rolling(window=trail2).mean().round(1)
    df['tr'] = pd.concat([df['High'] - df['Low'], (df['High'] - df[triggerPrice]).abs(), (df['Low'] - df[triggerPrice]).abs()], axis=1).max(axis=1)
    df['atr' + str(trail1)] = df['tr'].rolling(window=trail1).mean()
    df['atr' + str(trail2)] = df['tr'].rolling(window=trail2).mean()
    df['volatility' + str(trail1)] = df['Close'].rolling(window=trail1).std().round(1)
    df['volatility' + str(trail2)] = df['Close'].rolling(window=trail2).std().round(1)
    df['ema' + str(trail1)] = df[triggerPrice].ewm(span=trail1).mean()
    df['ema' + str(trail2)] = df[triggerPrice].ewm(span=trail2).mean()
    df['upperBb'] = df['Close'].rolling(window=trail1).mean() + (df['Close'].rolling(window=trail1).std() * factor1)
    for i in range(1, signalLookback + 1):
        if (df['High'].iloc[i] > df['upperBB'].shift(1).iloc[i]) and df['volume' + str(trail1)] < df['volume' + str(trail2)] and df['volatility' + str(trail1)] < df['volatility' + str(trail2)] and df['atr' + str(trail1)] < df['atr' + str(trail2)] and (df['Volume'].iloc[i] > (df['volume' + str(trail1)].shift(1).iloc[i] * factor1)):
            tradeSignalsTickerDate.append((stockName, df.index[i]))

# LOOP TROUGH UNIVERSE - KEEP TICKERS ONLY
for stockName, ticker in dachTickerDict.items():
    if ticker in sampledTickers:
        try:
            df = yf.download(ticker, start=startDate, end=endDate)
            if not df.empty:
                miniVcp()
        except Exception as e:
            print(f"Error downloading data for {stockName} ({ticker}): {e}")

# CLEAN OUT CONSECUTIVE SIGNALS
for stockName, signalDate in tradeSignalsTickerDate:
    if stockName not in seenTickers or signalDate - seenTickers[stockName] > signalBlock:
        seenTickers[stockName] = signalDate
        cleanedTradeSignals.append((stockName, signalDate))
tradeSignalsTickerDate = cleanedTradeSignals

# YFINANCE DATA FOR FILTERED STOCKS
tradeSignalsFullData = {}
for stockName, signalDate in tradeSignalsTickerDate:
    ticker = dachTickerDict[stockName]
    priceData = yf.download(ticker, start=startDate, end=endDate)
    infoData = {key: yf.Ticker(ticker).info[key] for key in selectedDataPoints}
    tradeSignalsFullData[stockName] = {'price': priceData, 'info': infoData, 'signals': [signalDate]}

# PLOTS
def signalsDash():
    numRows = len(tradeSignalsFullData)
    subplotTitles = [item for sublist in zip(list(tradeSignalsFullData.keys())[:numRows], [None] * numRows) for item in sublist]
    fig = make_subplots(
        rows=numRows, cols=2, column_widths=[0.7, 0.3], shared_xaxes=True, vertical_spacing=0.1, 
        subplot_titles=subplotTitles, specs=[[{"type": "xy", "secondary_y": True}, {"type": "table"}] for _ in range(numRows)])
    for i, (stockName, data) in enumerate(list(tradeSignalsFullData.items())[:numRows]):
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
def signals3D():
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    xAxisTicker = list(tradeSignalsFullData.keys())
    yAxisDate = [date.strftime('%Y-%m-%d') for date in tradeSignalsFullData[xAxisTicker[0]]['price'].index.date]
    zAxisVariable = [tradeSignalsFullData[ticker]['price']['Close'].pct_change().fillna(0).add(1).cumprod().values for ticker in xAxisTicker]
    zAxisVariable = [np.array(performance) * 100 - 100 for performance in zAxisVariable]

    signalDates = [tradeSignalsFullData[ticker]['signals'] for ticker in xAxisTicker]

    minLength = min(len(yAxisDate), min(len(z) for z in zAxisVariable))
    yAxisDate, zAxisVariable = yAxisDate[:minLength], [z[:minLength] for z in zAxisVariable]

    displayedDates = np.linspace(0, len(yAxisDate) - 1, 6, dtype=int)

    for i in range(len(xAxisTicker)):
        ax.plot([i] * len(yAxisDate), list(range(len(yAxisDate))), zAxisVariable[i], color='navy')

        signalIndices = [yAxisDate.index(date.strftime('%Y-%m-%d')) for date in signalDates[i]]
        ax.scatter([i] * len(signalIndices), signalIndices, zAxisVariable[i][signalIndices], c='gold', marker='o')

    xAxisTicker = [ticker[:3] for ticker in xAxisTicker]
    yAxisDate = [yAxisDate[i] for i in displayedDates]
    ax.set_xticks(list(range(len(xAxisTicker))))
    ax.set_xticklabels(xAxisTicker, rotation=45)
    ax.set_yticks(displayedDates)
    ax.set_yticklabels(yAxisDate)
    ax.set_zlabel('(%)') 

    ax.xaxis.line.set_color('black')
    ax.yaxis.line.set_color('purple')
    ax.zaxis.line.set_color('navy')

    plt.tight_layout()
    plt.show()
def results3D():
    tradePerformance = {}
    for stockName, signalDate in tradeSignalsTickerDate:
        df = tradeSignalsFullData[stockName]['price']
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
    tickerNames = [stockName for stockName, _ in tradeSignalsTickerDate for _ in tradePerformance.get(stockName, [])]
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

# MAIN
signals3D()
