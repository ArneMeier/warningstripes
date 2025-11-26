import numpy as np
import matplotlib.pyplot as plt
import requests
from matplotlib.patches import Rectangle
import matplotlib.colors as mcolors

def download_and_parse_berkeley_earth(url):
    response = requests.get(url)
    response.raise_for_status()
    lines = response.text.splitlines()

    years = []
    anomaly = []
    for line in lines:
        if line.startswith("%") or not line.strip():
            continue
        parts = line.split()
        try:
            year = int(float(parts[0]))
            temp = float(parts[1])
        except Exception:
            continue
        years.append(year)
        anomaly.append(temp)
    return np.array(years), np.array(anomaly)

def create_warm_to_darkpurple_cmap(warm_rgb, dark_hex="#240627"):
    dark_rgb = mcolors.to_rgb(dark_hex)
    colors = [warm_rgb, dark_rgb]
    cmap = mcolors.LinearSegmentedColormap.from_list("WarmToDarkPurple", colors)
    return cmap

def custom_cmap(val, vmin, vmax, cmap1, cmap2):
    norm = (val - vmin) / (vmax - vmin)
    norm = np.clip(norm, 0, 1)
    if norm <= 0.5:
        return cmap1(norm * 2)
    else:
        return cmap2((norm - 0.5) * 2)

def create_extended_rcp_projections(offset, rcp_targets_2100, rcp_targets_2200, last_year, total_years):
    projections = {}
    years_future = np.arange(last_year + 1, last_year + total_years + 1)  # roughly 200 years ahead
    years_2100 = 2100
    years_2200 = 2200

    for rcp in rcp_targets_2100.keys():
        start_val = offset
        target_2100 = rcp_targets_2100[rcp]
        target_2200 = rcp_targets_2200[rcp]

        years_points = np.array([last_year, years_2100, years_2200])
        temps_points = np.array([start_val, target_2100, target_2200])

        temps_interp = np.interp(years_future, years_points, temps_points)
        projections[rcp] = temps_interp

    return years_future, projections

def plot_warming_stripes(years, anomaly, start_idx, rcp_projections, vmin, vmax, cmap1, cmap2, years_future):
    fig, ax = plt.subplots(figsize=(16,6))

    last_third_years = years[start_idx:]
    last_third_anom = anomaly[start_idx:]

    # Plot last third historical data
    for year, temp in zip(last_third_years, last_third_anom):
        color = custom_cmap(temp, vmin, vmax, cmap1, cmap2)
        rect = Rectangle((year, 0), 1, 1, color=color, ec=None)
        ax.add_patch(rect)

    # Plot RCP projections from years_future
    y_pos = 1.2
    height = 0.3
    for rcp_name in ['RCP8.5', 'RCP6.0', 'RCP4.5', 'RCP2.6']:
        vals = rcp_projections[rcp_name]
        for i, temp in enumerate(vals):
            year = years_future[i]
            color = custom_cmap(temp, vmin, vmax, cmap1, cmap2)
            rect = Rectangle((year, y_pos), 1, height, color=color, ec=None)
            ax.add_patch(rect)
        ax.text(years_future[-1] + 5, y_pos + height/2,
                rcp_name, verticalalignment='center', fontsize=11)
        y_pos += height + 0.1

    ax.set_xlim(last_third_years[0], years_future[-1] + 20)
    ax.set_ylim(0, y_pos)
    ax.axis('off')
    ax.set_title("Warming Stripes: Extended RCP pathways with warm-to-dark purple scale")
    plt.show()

if __name__ == "__main__":
    url = "https://berkeley-earth-temperature.s3.us-west-1.amazonaws.com/Global/Complete_TAVG_summary.txt"
    years, anomaly = download_and_parse_berkeley_earth(url)

    n = len(anomaly)
    start_idx = 2 * n // 3
    last_third_anom = anomaly[start_idx:]

    offset = last_third_anom[-1]
    x_shifted = last_third_anom - offset

    # RCP 2100 and 2200 targets relative to last historical anomaly
    rcp_targets_2100 = {
        'RCP2.6': offset + 1.9,
        'RCP4.5': offset + 2.87,
        'RCP6.0': offset + 3.1,
        'RCP8.5': offset + 4.8
    }

    rcp_targets_2200 = {
        'RCP2.6': offset + 1.4,
        'RCP4.5': offset + 2.8,
        'RCP6.0': offset + 3.7,
        'RCP8.5': offset + 7.8
    }

    total_projection_years = 100  # roughly 100 years

    years_future, rcp_projections = create_extended_rcp_projections(
        offset,
        rcp_targets_2100,
        rcp_targets_2200,
        years[-1],
        total_projection_years
    )

    vmin = np.min(last_third_anom)  # coldest start of last third
    vmax = np.max(rcp_projections['RCP8.5'])  # warmest max RCP8.5 at 2200

    cmap1 = plt.get_cmap('coolwarm')
    warm_rgb = cmap1(1.0)[:3]  # warmest color RGB of coolwarm
    cmap2 = create_warm_to_darkpurple_cmap(warm_rgb, "#240627")

    plot_warming_stripes(years, anomaly, start_idx, rcp_projections, vmin, vmax, cmap1, cmap2, years_future)
