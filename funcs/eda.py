# funcs/eda.py
from pathlib import Path
import pandas as pd, matplotlib.pyplot as plt
plt.rcParams["font.family"]="Malgun Gothic"; plt.rcParams["axes.unicode_minus"]=False

util = pd.read_csv(Path("data")/"station_utilization_latest.csv", encoding="utf-8-sig")
util["avail_ratio"] = pd.to_numeric(util["avail_ratio"], errors="coerce")

# 1) 분포
plt.figure(); util["avail_ratio"].dropna().plot(kind="hist", bins=20)
plt.title("가용률 분포"); plt.xlabel("avail_ratio"); plt.ylabel("count"); plt.tight_layout(); plt.show()

# 2) 핫스팟 TOP10
hot = util.sort_values("avail_ratio").head(10)
plt.figure(); plt.barh(hot["station_name"], hot["avail_ratio"])
plt.title("핫스팟 TOP10(가용률 낮음)"); plt.xlabel("avail_ratio"); plt.gca().invert_yaxis()
plt.tight_layout(); plt.show()
