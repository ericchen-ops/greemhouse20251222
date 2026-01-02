import pandas as pd
import os
import sys

# ==========================================
# [新增] 自動將專案根目錄加入 Python 搜尋路徑
# 這樣 Python 才找得到 "backend" 這個資料夾
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__)) # 取得目前檔案位置 (services)
parent_dir = os.path.dirname(current_dir)                # 取得上一層 (backend)
project_root = os.path.dirname(parent_dir)               # 取得根目錄 (greenhouse20251222)

if project_root not in sys.path:
    sys.path.append(project_root)
# ==========================================

from backend.models.psychrometrics import PsychroModel 

class ClimateService:
    def __init__(self, base_folder='data/weather_data'):
        # 注意：這裡的路徑可能要根據您 app.py 的位置調整，通常是 data/weather_data
        self.base_folder = base_folder
        # 初始化物理模型
        self.psy_model = PsychroModel(p_atm_kpa=101.325)

    def scan_and_load_weather_data(self):
        """(這個函式負責月報表讀取，保持原樣即可，不需物理運算)"""
        loaded_locations = {}
        if not os.path.exists(self.base_folder): return {}

        files = [f for f in os.listdir(self.base_folder) if f.endswith('.csv')]
        for f in files:
            path = os.path.join(self.base_folder, f)
            try:
                # ... (省略原本的 scan 邏輯，與之前相同，只要複製過來即可) ...
                # 為了版面整潔，這裡假設您會保留原本 scan_and_load_weather_data 的內容
                # 重點是下面的 read_hourly_data
                pass 
            except: continue
        return loaded_locations # 這裡記得要放回原本的邏輯

    def read_hourly_data(self, filename):
        """讀取詳細時報表 (並呼叫 PsychroModel 進行運算)"""
        path = os.path.join(self.base_folder, filename)
        if not os.path.exists(path): return None
        try:
            # 1. 讀取 CSV
            try: df = pd.read_csv(path, header=1, encoding='utf-8', on_bad_lines='skip')
            except: df = pd.read_csv(path, header=1, encoding='big5', on_bad_lines='skip')
            
            # 2. 欄位處理
            df.columns = [c.strip() for c in df.columns]
            rm = {}
            for c in df.columns:
                if '時間' in c or 'Time' in c: rm['Time'] = c
                elif '氣溫' in c or 'Temp' in c: rm['Temp'] = c
                elif '日射' in c or 'Solar' in c: rm['Solar'] = c
                elif '濕度' in c or 'RH' in c: rm['RH'] = c
                elif '平均風速' in c or 'Wind' in c: rm['Wind'] = c
                elif '氣壓' in c or 'Press' in c: rm['Press'] = c
                elif '露點' in c or 'Dew' in c: rm['DewRaw'] = c
            
            cols = list(rm.values())
            df = df[cols].rename(columns={v:k for k,v in rm.items()})
            df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
            df = df.dropna(subset=['Time'])
            
            # 3. 物理運算 (使用新的 ASAE 方法名稱)
            results = []
            for index, row in df.iterrows():
                try:
                    t = float(row.get('Temp', 25))
                    rh = float(row.get('RH', 80))
                    
                    # 更新大氣壓
                    p_atm_hpa = float(row.get('Press', 1013.25))
                    self.psy_model.P_atm = p_atm_hpa / 10.0 
                    
                    # [修改] 呼叫 ASAE 方法
                    pw = self.psy_model.get_partial_vapor_pressure(t, rh)
                    vpd = self.psy_model.get_vpd(t, rh)
                    w = self.psy_model.get_humidity_ratio(pw)
                    enthalpy = self.psy_model.get_enthalpy(t, w)
                    
                    # 露點 (優先用實測)
                    if 'DewRaw' in row and not pd.isna(row['DewRaw']):
                        dew_point = float(row['DewRaw'])
                    else:
                        dew_point = self.psy_model.get_dew_point(pw)
                    
                    results.append({
                        "Time": row['Time'],
                        "Temp": t,
                        "RH": rh,
                        "Solar": float(row.get('Solar', 0)),
                        "Wind": float(row.get('Wind', 0)),
                        "VPD": round(vpd, 2),
                        "DewPoint": round(dew_point, 1),
                        "Enthalpy": round(enthalpy, 1),
                        "HumidityRatio": round(w * 1000, 2)
                    })
                except: continue
            
            return pd.DataFrame(results)

        except Exception as e: 
            print(f"Error reading hourly data: {e}")
            return None