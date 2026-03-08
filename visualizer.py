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
        
    # Set physics and interaction layout options
    net.set_options("""
    var options = {
      "interaction": {
        "hover": true
      },
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
    
    # Add custom CSS for scrollable tooltips (useful for mobile)
    with open(output_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    custom_css_js = """
    <style>
    /* Hide the default vis.js tooltip entirely */
    .vis-tooltip {
        display: none !important;
    }
    
    /* Custom overlay for mobile-friendly scrollable info */
    #custom-tooltip-overlay {
        display: none;
        position: absolute;
        top: 10px;
        right: 10px;
        width: 250px;
        max-height: 80%;
        overflow-y: auto;
        background: rgba(255, 255, 255, 0.95);
        border: 1px solid #ccc;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 9999;
        font-size: 14px;
        pointer-events: auto; /* allow touching/scrolling */
        touch-action: pan-y;
    }
    
    /* Close button for mobile */
    #custom-tooltip-close {
        float: right;
        cursor: pointer;
        font-weight: bold;
        color: #888;
        font-size: 18px;
        line-height: 1;
        margin-left: 10px;
    }
    </style>
    
    <div id="custom-tooltip-overlay">
        <span id="custom-tooltip-close">&times;</span>
        <div id="custom-tooltip-content"></div>
    </div>
    
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // Wait for network to be initialized by vis.js
        var checkNetwork = setInterval(function() {
            if (typeof network !== 'undefined' && typeof nodes !== 'undefined') {
                clearInterval(checkNetwork);
                
                var overlay = document.getElementById("custom-tooltip-overlay");
                var content = document.getElementById("custom-tooltip-content");
                var closeBtn = document.getElementById("custom-tooltip-close");
                
                // Function to show custom tooltip
                function showTooltip(nodeId) {
                    var node = nodes.get(nodeId);
                    if(node && node.title) {
                        content.innerHTML = "<strong>" + node.label + "</strong><br><hr style='margin: 5px 0'>" + node.title.replace(/\\n/g, "<br>");
                        overlay.style.display = "block";
                    }
                }
                
                // 1. Mobile & Desktop Tap/Click
                network.on("click", function (params) {
                    if(params.nodes.length > 0) {
                        showTooltip(params.nodes[0]);
                    } else {
                        // Clicked on background, close it
                        overlay.style.display = "none";
                    }
                });
                
                // 2. Desktop Hover
                network.on("hoverNode", function (params) {
                    showTooltip(params.node);
                });
                
                // Close button logic
                closeBtn.onclick = function() {
                    overlay.style.display = "none";
                };
            }
        }, 200);
        
        // Stop event propagation to prevent the canvas from panning when scrolling the tooltip
        var stopProp = function(e) {
            if (e.target.closest('#custom-tooltip-overlay')) {
                e.stopPropagation();
            }
        };
        document.addEventListener('wheel', stopProp, {capture: true, passive: false});
        document.addEventListener('touchstart', stopProp, {capture: true, passive: false});
        document.addEventListener('touchmove', stopProp, {capture: true, passive: false});
        document.addEventListener('touchend', stopProp, {capture: true, passive: false});
    });
    </script>
    """
    
    # Inject before </body> because we are inserting a <div>
    if "</body>" in html:
        html = html.replace("</body>", f"{custom_css_js}</body>")
    else:
        html += custom_css_js
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
