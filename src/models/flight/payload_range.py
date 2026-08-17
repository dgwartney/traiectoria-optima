import matplotlib.pyplot as plt

def plot_payload_range_diagram():
    # Structural Boundary Points derived from model calculations
    # Format: (Range in nmi, Payload in kg)
    points = {
        'A': (0, 52500),         # Max Structural Payload (MZFW Limit)
        'B': (4820, 52500),      # Max Payload at MTOW Limit
        'C': (7850, 24161),      # Max Fuel Tanks Full at MTOW Limit
        'D': (8920, 0)           # Ferry Range (Zero Payload)
    }

    # Extract coordinates for plotting
    ranges = [points['A'][0], points['B'][0], points['C'][0], points['D'][0]]
    payloads = [points['A'][1], points['B'][1], points['C'][1], points['D'][1]]

    # Initialize Plot
    plt.figure(figsize=(10, 6), dpi=100)
    
    # Plot Envelope Boundary Line
    plt.plot(ranges, payloads, color='#003366', linewidth=2.5, label='Payload-Range Boundary', zorder=2)
    
    # Fill allowable operating region
    plt.fill_between(ranges, payloads, color='#003366', alpha=0.1, label='Flyable Operational Envelope')

    # Scatter points A, B, C, D
    plt.scatter(ranges, payloads, color='#cc0000', s=60, zorder=3)

    # Annotate Key Inflection Points
    plt.annotate('Point A\n(Max Structural Payload)', xy=points['A'], xytext=(150, 50000),
                 arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=6))
    
    plt.annotate('Point B (MTOW Limit)\nMax Payload Range', xy=points['B'], xytext=( points['B'][0] - 800, 42000),
                 arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=6))
    
    plt.annotate('Point C (Max Fuel)\nPayload Offloaded for Fuel', xy=points['C'], xytext=(points['C'][0] - 1200, 12000),
                 arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=6))
    
    plt.annotate('Point D\nFerry Range', xy=points['D'], xytext=(points['D'][0] - 900, 4000),
                 arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=6))

    # Reference Structural Limit Lines
    plt.axhline(y=52500, color='gray', linestyle='--', alpha=0.6, label='Max Structural Payload Limit (MZFW - OEW)')

    # Labels and Styling
    plt.title('Boeing 787-9 Payload-Range Operational Envelope', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Operational Range (Nautical Miles - nmi)', fontsize=11, labelpad=10)
    plt.ylabel('Payload Mass (kg)', fontsize=11, labelpad=10)
    
    plt.xlim(-200, 10000)
    plt.ylim(-2000, 60000)
    
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(loc='upper right', frameon=True)
    plt.tight_layout()

    # Display Graph
    plt.show()

if __name__ == '__main__':
    plot_payload_range_diagram()