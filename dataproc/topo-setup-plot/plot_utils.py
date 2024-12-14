import os
import matplotlib.pyplot as plt
from output_data import *

def get_figure_title(fixed_options):
    dirname_elements = []
    for fixed_option_key, fixed_option_value in fixed_options.items():
        dirname_elements.append(fixed_option_key)
        dirname_elements.append(fixed_option_value)
    return '--'.join(dirname_elements)


def plot_one_figure(
        df, fixed_options, curve_option_keys,
        x_value_type, y_value_type,
        output_dir, overwrite):
    # Check whether need plotting
    output_filename = get_figure_filename(
        x_value_type, y_value_type)
    output_filepath = os.path.join(
        output_dir, output_filename)
    if os.path.exists(output_filepath) and not overwrite:
        print(f"Figure already exists: {output_filepath}")

    # Create a figure and axis
    plt.figure(figsize=(10, 6))

    # Iterate through unique curves
    for curve_option_values, figure_df in df.groupby(curve_option_keys):
        sorted_figure_df = figure_df.sort_values(by=x_value_type)
        curve_options = dict(zip(curve_option_keys, curve_option_values))
        plt.plot(
            sorted_figure_df[x_value_type],
            sorted_figure_df[y_value_type],
            marker='o',
            label=f'{curve_options}'
        )

    # Label different topology
    for topo_type, topo_df in df.groupby('t'):
        for x_value in df[x_value_type].unique():
            sub_df = df[df[x_value_type] == x_value]
            max_e_row = sub_df[sub_df[x_value_type] == sub_df[x_value_type].max()].iloc[0]
            plt.axvline(x=x_value, linestyle='--', color='gray', alpha=0.5)
            plt.text(x_value, max_e_row[x_value_type], str(max_e_row['topo_name']), verticalalignment='bottom', horizontalalignment='center')

    # for _, row in df.iterrows():
    #     if row[x_scale] not in labeled_x_values:
    #         plt.axvline(x=row[x_scale], linestyle='--', color='gray', alpha=0.5)
    #         plt.text(row[x_scale], row[y_value], str(row['topo_name']), verticalalignment='bottom', horizontalalignment='center')
    #         labeled_x_values.add(row[x_scale])

    # Adding labels and title
    title = get_figure_title(fixed_options)
    plt.xlabel(x_value_type)
    plt.ylabel(y_value_type)
    plt.title(title)
    plt.legend()
    plt.grid()

    # Save figure
    plt.savefig( output_filepath, bbox_inches='tight')
    plt.close()
