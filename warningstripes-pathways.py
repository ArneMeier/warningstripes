import numpy as np
import matplotlib.pyplot as plt
import requests
from matplotlib.patches import Rectangle
import matplotlib.colors as mcolors

# Function to download and parse Berkeley Earth temperature anomaly data
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

# Create a custom colormap from warm color to dark purple
def create_warm_to_darkpurple_cmap(warm_rgb, dark_hex="#240627"):
    dark_rgb = mcolors.to_rgb(dark_hex)
    colors = [warm_rgb, dark_rgb]
    cmap = mcolors.LinearSegmentedColormap.from_list("WarmToDarkPurple", colors)
    return cmap

# Custom colormap function that blends two colormaps based on value
def custom_cmap(val, vmin, vmax, cmap1, cmap2):
    norm = (val - vmin) / (vmax - vmin)
    norm = np.clip(norm, 0, 1)
    if norm <= 0.5:
        return cmap1(norm * 2)
    else:
        return cmap2((norm - 0.5) * 2)

# Create extended RCP projections by copying historical fluctuations and adding linear ramps
def create_extended_rcp_projections(years, anomaly, copy_start_year, copy_end_year,
                                    rcp_targets_2100, rcp_targets_2200):
    # 1. Extract the copy interval [copy_start_year..copy_end_year]
    idx_start = np.searchsorted(years, copy_start_year)
    idx_end = np.searchsorted(years, copy_end_year) + 1  # inclusive
    historical_segment = anomaly[idx_start:idx_end]
    segment_years = years[idx_start:idx_end]

    # 2. Compute offset: difference between last year (2024) value and first copy year (1848)
    offset = historical_segment[-1] - historical_segment[0]

    # 3. Shift segment by adding offset to all values (to ensure smooth baseline)
    shifted_segment = historical_segment + offset

    # Projection years: from copy_end_year+1 to 2200
    proj_years = np.arange(copy_end_year + 1, 2201)
    n_proj = len(proj_years)

    # 4. Construct warming ramps from 0 (at first projection year) to target RCP values at 2100 and 2200 relative to baseline + offset
    projections = {}
    years_2100 = 2100
    years_2200 = 2200
    for rcp in rcp_targets_2100.keys():
        # Linear ramp values start at 0 at first projection year and reach differential warming at 2100 and 2200
        years_points = np.array([copy_end_year, years_2100, years_2200])
        # ramp is relative warming above shifted baseline (offset)
        temps_points = np.array([0,
                                 rcp_targets_2100[rcp],
                                 rcp_targets_2200[rcp]])
        linear_ramp = np.interp(proj_years, years_points, temps_points)

        # 5. Add the linear warming ramp onto the shifted historical segment repeated or truncated to match projection length
        # Repeat shifted segment if too short, or truncate if too long
        repeat_factor = int(np.ceil(n_proj / len(shifted_segment)))
        extended_fluctuations = np.tile(shifted_segment, repeat_factor)[:n_proj]

        projections[rcp] = extended_fluctuations + linear_ramp + offset

    return segment_years, shifted_segment, proj_years, projections

# Plotting function
# Plot historical copied segment as vertical color bars
# Plot RCP projections as adjacent vertical color bars stacked without gap
def plot_warming_stripes(years, anomaly, segment_years, segment_anom, proj_years, projections,
                         vmin, vmax, cmap1, cmap2):
    fig, ax = plt.subplots(figsize=(16,6))

    # Plot copied historical segment as vertical color bars
    for year, temp in zip(segment_years, segment_anom):
        color = custom_cmap(temp, vmin, vmax, cmap1, cmap2)
        rect = Rectangle((year, 0), 1, 1, color=color, ec=None)
        ax.add_patch(rect)

    # Plot RCP projections as adjacent vertical color bars stacked without gap
    y_pos = 0
    height = 0.2
    for rcp_name in ['RCP8.5', 'RCP6.0', 'RCP4.5', 'RCP2.6']:
        vals = projections[rcp_name]
        for i, temp in enumerate(vals):
            year = proj_years[i]
            color = custom_cmap(temp, vmin, vmax, cmap1, cmap2)
            rect = Rectangle((year, y_pos), 1, height, color=color, ec=None)
            ax.add_patch(rect)
        ax.text(proj_years[-1] + 5, y_pos + height/2,
                rcp_name, verticalalignment='center', fontsize=11)
        y_pos += height

    ax.set_xlim(segment_years[0], proj_years[-1] + 20)
    ax.set_ylim(0, y_pos)
    ax.axis('off')
    ax.set_title("Warming Stripes with copied fluctuations and linear ramps")

    # Positions for labels:
    label_y_pos = -0.01  # slightly below the x-axis baseline (adjust as needed)
    ax.text(1850, label_y_pos, "1850", ha='center', va='top', fontsize=12)
    ax.text(years[-1], label_y_pos, "Now", ha='center', va='top', fontsize=12)
    ax.text(2200, label_y_pos, "2200", ha='center', va='top', fontsize=12)
    
    # Adjust axes limits if needed to make space for text:
    ax.set_xlim(min(1850, segment_years[0]), 2220)
    ax.set_ylim(label_y_pos - 0.1, ax.get_ylim()[1])  # extend lower limit a bit for label visibility

    # RCP Explanations labels, text align is right and font in white text color, position is over the rcp path way plot at the rear end, thin font
    label_x_pos_explanations = 2190
    ax.text(label_x_pos_explanations, 0.7, "Emissions peak by 2030\nnegative emissions by 2080\n+1.9°C in 2100, +1.4°C by 2200", ha='right', va='center', fontsize=10, color='white')
    ax.text(label_x_pos_explanations, 0.5, "Emissions peak by 2050\n+2.7°C in 2100, +2.8°C by 2200", ha='right', va='center', fontsize=10, color='white')
    ax.text(label_x_pos_explanations, 0.3, "Emissions peak by 2090\n+3.1°C in 2100, +3.7°C by 2200", ha='right', va='center', fontsize=10, color='white')
    ax.text(label_x_pos_explanations, 0.1, "Emissions peak between 2100-2150\n+4.8°C in 2100, +7.8°C by 2200", ha='right', va='center', fontsize=10, color='white')

    # Export to SVG and PDF
    plt.savefig("warming_stripes.svg", format='svg', bbox_inches='tight')
    plt.savefig("warming_stripes.pdf", format='pdf', bbox_inches='tight')

    plt.show()


if __name__ == "__main__":
    url = "https://berkeley-earth-temperature.s3.us-west-1.amazonaws.com/Global/Complete_TAVG_summary.txt"
    years, anomaly = download_and_parse_berkeley_earth(url)

    # Settings for copying segment and extending projections
    copy_start_year = 1848
    copy_end_year = 2024  # last year of Berkeley Earth data used

    # RCP targets in degrees relative to baseline (the first value of copied segment shifted by offset)
    rcp_targets_2100 = {
        'RCP2.6': 1.9,
        'RCP4.5': 2.87,
        'RCP6.0': 3.1,
        'RCP8.5': 4.8
    }

    rcp_targets_2200 = {
        'RCP2.6': 1.4,
        'RCP4.5': 2.8,
        'RCP6.0': 3.7,
        'RCP8.5': 7.8
    }

    segment_years, shifted_segment, proj_years, projections = create_extended_rcp_projections(
        years, anomaly, copy_start_year, copy_end_year,
        rcp_targets_2100, rcp_targets_2200)

    # Color scale min and max covers all projected values plus copied segment
    vmin = np.min(np.concatenate([shifted_segment] + [v for v in projections.values()]))
    vmax = np.max(np.concatenate([shifted_segment] + [v for v in projections.values()]))

    cmap1 = plt.get_cmap('coolwarm')
    warm_rgb = cmap1(1.0)[:3]
    cmap2 = create_warm_to_darkpurple_cmap(warm_rgb, "#240627")

    plot_warming_stripes(years, anomaly, segment_years, shifted_segment,
                         proj_years, projections, vmin, vmax, cmap1, cmap2)
