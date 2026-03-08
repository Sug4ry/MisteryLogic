from pyvis.network import Network
from models import MysteryState
import os

def generate_relationship_graph(state: MysteryState, chapter: int, output_path: str):
    # Initialize a pyvis network
    net = Network(height="600px", width="100%", directed=False, notebook=False, bgcolor="#ffffff", font_color="black")
    
    # Add nodes for each character
    for char in state.characters:
        color = "#95A5A6" # Grey (不明)
        if char.status == "生存":
            color = "#2ECC71" # Green
        elif char.status == "死亡":
            color = "#E74C3C" # Red

        # Construct tooltip/title with history up to current chapter
        title_lines = [f"役割: {char.role}", f"状態: {char.status}", ""]
        
        # Filter history up to requested chapter
        history_keys = sorted([int(k) for k in char.relationship_history.keys() if int(k) <= chapter])
        if history_keys:
            title_lines.append("[関係性履歴]")
            for k in history_keys:
                val = char.relationship_history.get(k) or char.relationship_history.get(str(k))
                title_lines.append(f"第{k}章: {val}")
        else:
            title_lines.append("関係性の履歴なし")

        net.add_node(char.name, label=char.name, title="\n".join(title_lines), color=color)

    # Add edges based on timeline interactions up to current chapter
    interactions = set()
    for tl in state.timelines:
        if tl.chapter_number <= chapter:
            # Connect all involved persons in an event
            people = tl.involved_persons
            for i in range(len(people)):
                for j in range(i + 1, len(people)):
                    p1, p2 = people[i], people[j]
                    # Verify both names exist in characters to avoid errors
                    if any(c.name == p1 for c in state.characters) and any(c.name == p2 for c in state.characters):
                        # Sort alphabetically to treat (A, B) and (B, A) as same edge
                        edge = tuple(sorted([p1, p2]))
                        interactions.add(edge)

    for p1, p2 in interactions:
        net.add_edge(p1, p2)
        
    # Set physics layout options
    net.set_options("""
    var options = {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -100,
          "centralGravity": 0.01,
          "springLength": 200
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based"
      }
    }
    """)
    
    # Generate HTML
    net.save_graph(output_path)
