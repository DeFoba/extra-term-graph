import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

def draw_architecture():
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis('off')

    # Define blocks
    blocks = [
        {"id": "pdf", "label": "PDF Documents\n(Corpus)", "x": 0.1, "y": 0.5, "w": 0.15, "h": 0.2, "color": "#e0f7fa"},
        {"id": "corpus", "label": "corpus.py\n(Parsing & Clean)", "x": 0.3, "y": 0.5, "w": 0.15, "h": 0.2, "color": "#ffecb3"},
        {"id": "keywords", "label": "keywords.py\n(TF-IDF + KeyBERT)", "x": 0.5, "y": 0.7, "w": 0.15, "h": 0.2, "color": "#c8e6c9"},
        {"id": "summary", "label": "summarization.py\n(MMR Algorithm)", "x": 0.5, "y": 0.3, "w": 0.15, "h": 0.2, "color": "#c8e6c9"},
        {"id": "graph", "label": "graph.py\n(Jaccard & Cosine)", "x": 0.7, "y": 0.5, "w": 0.15, "h": 0.2, "color": "#ffcdd2"},
        {"id": "neo4j", "label": "Neo4j Aura DB\n(Graph Visual)", "x": 0.9, "y": 0.5, "w": 0.15, "h": 0.2, "color": "#d1c4e9"},
    ]

    for b in blocks:
        rect = patches.FancyBboxPatch(
            (b["x"] - b["w"]/2, b["y"] - b["h"]/2), b["w"], b["h"], 
            boxstyle="round,pad=0.02", facecolor=b["color"], edgecolor="black", lw=1.5
        )
        ax.add_patch(rect)
        ax.text(b["x"], b["y"], b["label"], ha="center", va="center", fontsize=10, fontweight='bold', wrap=True)

    # Define arrows
    arrows = [
        ("pdf", "corpus"),
        ("corpus", "keywords"),
        ("corpus", "summary"),
        ("keywords", "graph"),
        ("summary", "graph"),
        ("graph", "neo4j"),
    ]

    def get_coords(bid):
        for b in blocks:
            if b["id"] == bid:
                return b["x"], b["y"], b["w"], b["h"]
        return 0, 0, 0, 0

    for src, dst in arrows:
        sx, sy, sw, sh = get_coords(src)
        dx, dy, dw, dh = get_coords(dst)
        
        # Calculate arrow start and end
        if sx < dx:  # left to right
            start_x = sx + sw/2
            end_x = dx - dw/2
            start_y, end_y = sy, dy
        elif sy < dy: # bottom to top
            start_x, end_x = sx, dx
            start_y = sy + sh/2
            end_y = dy - dh/2
        else: # top to bottom
            start_x, end_x = sx, dx
            start_y = sy - sh/2
            end_y = dy + dh/2

        ax.annotate('', xy=(end_x, end_y), xytext=(start_x, start_y),
                    arrowprops=dict(facecolor='black', edgecolor='black', arrowstyle="->", lw=1.5))

    plt.title("Архитектура конвейера (Data Pipeline) Extra-Term-Graph", fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    
    out_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "pipeline_arch.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    print(f"Архитектура сохранена в {out_path}")

if __name__ == "__main__":
    draw_architecture()
