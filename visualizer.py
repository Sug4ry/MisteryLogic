from pyvis.network import Network
from models import MysteryState
import os

def generate_relationship_graph(state: MysteryState, chapter: int, output_path: str):
    # Initialize a pyvis network
    net = Network(height="600px", width="100%", directed=False, notebook=False, bgcolor="#ffffff", font_color="black")
    
    # Add nodes for each character
    active_characters = [c for c in state.characters if not getattr(c, 'is_ignored', False)]
    active_char_names = {c.name for c in active_characters}
    
    for char in active_characters:
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
                    # Verify both names exist in active characters to avoid errors and hide ignored
                    if p1 in active_char_names and p2 in active_char_names:
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

def generate_murder_board_graph(state: MysteryState, output_path: str, filter_suspect: str = None):
    # Dark mode config
    bgcolor = "#1e1e1e"
    font_color = "#ffffff"
    
    net = Network(height="600px", width="100%", directed=True, notebook=False, bgcolor=bgcolor, font_color=font_color)
    
    # Pre-gather data
    active_characters = [c for c in state.characters if not getattr(c, 'is_ignored', False)]
    active_char_names = {c.name for c in active_characters}
    
    active_motives = getattr(state, 'motives', [])
    active_motives = [m for m in active_motives if not getattr(m, 'is_ignored', False)]
    
    active_evidences = getattr(state, 'evidences', [])
    active_evidences = [e for e in active_evidences if not getattr(e, 'is_ignored', False)]
    
    active_timelines = getattr(state, 'timelines', [])
    
    # 1. Characters
    for char in active_characters:
        # Dimming logic based on filter
        is_dimmed = False
        if filter_suspect and filter_suspect != "すべて":
            # Check if char is connected to the filtered suspect
            connected = False
            if char.name == filter_suspect:
                connected = True
            else:
                # Check motives
                for m in active_motives:
                    if (m.suspect_name == filter_suspect and char.name in m.motive_content) or \
                       (m.suspect_name == char.name and filter_suspect in m.motive_content):
                        connected = True
                # Check evidences
                for e in active_evidences:
                    if (filter_suspect in e.affirming_persons + e.denying_persons) and \
                       (char.name in e.affirming_persons + e.denying_persons):
                        connected = True
                # Check timelines
                for tl in active_timelines:
                    if filter_suspect in tl.involved_persons and char.name in tl.involved_persons:
                        connected = True
            if not connected:
                is_dimmed = True

        # Icons & Colors
        color = "#7f8c8d" # 灰: 不明
        icon = "❓"
        mass = 1
        
        if char.status == "生存":
            color = "#27ae60" # 緑
            icon = "👤"
            if char.role and "主人公" in char.role or "探偵" in char.role:
                icon = "🕵️"
        elif char.status == "死亡":
            color = "#c0392b" # 赤
            icon = "💀"
            mass = 5 # Victims are heavier, stay near center
            
        if getattr(char, 'uncertainty', False):
            icon = "👻" # Uncertain person
            
        opacity = 0.2 if is_dimmed else 1.0
        
        # Apply opacity to hex color
        rgba_color = f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, {opacity})"
        
        label = f"{icon} {char.name}"
        title = f"役割: {char.role}\n状態: {char.status}"
        
        net.add_node(char.name, label=label, title=title, color=rgba_color, shape="ellipse", mass=mass)
        
    # 2. Motives
    for idx, motive in enumerate(active_motives):
        node_id = f"motive_{idx}"
        
        is_dimmed = False
        if filter_suspect and filter_suspect != "すべて" and motive.suspect_name != filter_suspect:
            is_dimmed = True
            
        opacity = 0.2 if is_dimmed else 1.0
        color = f"rgba(230, 126, 34, {opacity})" # Orange
        
        short_label = (motive.motive_content[:10] + '...') if len(motive.motive_content) > 10 else motive.motive_content
        icon = "💡"
        label = f"{icon} {short_label}"
        title = f"対象: {motive.suspect_name}\n内容: {motive.motive_content}\n強さ: {motive.strength}\n因縁: {motive.past_karma}"
        
        net.add_node(node_id, label=label, title=title, color=color, shape="box")
        
        # connect suspect -> motive
        if motive.suspect_name in active_char_names:
            uncertain = getattr(motive, 'uncertainty', False)
            edge_color = f"rgba(230, 126, 34, {opacity})"
            net.add_edge(motive.suspect_name, node_id, color=edge_color, dashes=uncertain, label="Why/動機", font={"color": edge_color, "size": 10})
            
    # 3. Evidences
    for idx, ev in enumerate(active_evidences):
        node_id = f"evidence_{idx}"
        
        is_dimmed = False
        if filter_suspect and filter_suspect != "すべて" and filter_suspect not in ev.affirming_persons + ev.denying_persons:
            is_dimmed = True
            
        opacity = 0.2 if is_dimmed else 1.0
        color = f"rgba(52, 152, 219, {opacity})" # Blue
        
        icon = "🔍"
        label = f"{icon} {ev.name}"
        title = f"発見場所: {ev.location_obtained}"
        
        net.add_node(node_id, label=label, title=title, color=color, shape="hexagon")
        
        uncertain = getattr(ev, 'uncertainty', False)
        
        # connect character -> evidence
        for p in ev.affirming_persons:
            if p in active_char_names:
                edge_color = f"rgba(46, 204, 113, {opacity})" # Green
                net.add_edge(node_id, p, color=edge_color, dashes=uncertain, label="肯定/アリバイ", arrows="to", font={"color": edge_color, "size": 10})
        for p in ev.denying_persons:
            if p in active_char_names:
                edge_color = f"rgba(231, 76, 60, {opacity})" # Red
                net.add_edge(node_id, p, color=edge_color, dashes=uncertain, label="否定/不利", arrows="to", font={"color": edge_color, "size": 10})

    # 4. Person to Person relationships (from timelines)
    interactions = {}
    for tl in active_timelines:
        uncertain = getattr(tl, 'uncertainty', False)
        people = tl.involved_persons
        for i in range(len(people)):
            for j in range(i + 1, len(people)):
                p1, p2 = people[i], people[j]
                if p1 in active_char_names and p2 in active_char_names:
                    edge = tuple(sorted([p1, p2]))
                    if edge not in interactions:
                        interactions[edge] = {"count": 1, "uncertain": uncertain}
                    else:
                        interactions[edge]["count"] += 1
                        interactions[edge]["uncertain"] = interactions[edge]["uncertain"] and uncertain

    for (p1, p2), data in interactions.items():
        is_dimmed = False
        if filter_suspect and filter_suspect != "すべて" and filter_suspect not in [p1, p2]:
            is_dimmed = True
            
        opacity = 0.15 if is_dimmed else 0.5
        edge_color = f"rgba(149, 165, 166, {opacity})"
        net.add_edge(p1, p2, color=edge_color, dashes=data["uncertain"], label="関係性", arrows="", font={"color": edge_color, "size": 8})

    net.set_options("""
    var options = {
      "nodes": {
        "borderWidth": 2,
        "shadow": true
      },
      "edges": {
        "smooth": {
          "type": "dynamic"
        },
        "shadow": true
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 200
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -150,
          "centralGravity": 0.02,
          "springLength": 250,
          "springConstant": 0.05
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based",
        "timestep": 0.35
      }
    }
    """)
    net.save_graph(output_path)
    
    custom_css_js = """
    <style>
    /* Hide the default vis.js tooltip entirely */
    .vis-tooltip {
        display: none !important;
    }
    
    /* Custom overlay for mobile-friendly scrollable info, themed for dark mode */
    #custom-tooltip-overlay {
        display: none;
        position: absolute;
        top: 10px;
        right: 10px;
        width: 300px;
        max-height: 80%;
        overflow-y: auto;
        background: rgba(30, 30, 30, 0.95);
        color: #ecf0f1;
        border: 1px solid #7f8c8d;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.5);
        z-index: 9999;
        font-size: 14px;
        pointer-events: auto; /* allow touching/scrolling */
        touch-action: pan-y;
        font-family: 'Courier New', Courier, monospace;
    }
    
    /* Close button for mobile */
    #custom-tooltip-close {
        float: right;
        cursor: pointer;
        font-weight: bold;
        color: #bdc3c7;
        font-size: 18px;
        line-height: 1;
        margin-left: 10px;
    }
    #custom-tooltip-close:hover {
        color: #e74c3c;
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
                
                function showTooltip(nodeId) {
                    var node = nodes.get(nodeId);
                    if(node && node.title) {
                        content.innerHTML = "<strong style='color:#f39c12; font-size:16px;'>" + node.label + "</strong><br><hr style='margin: 8px 0; border-color:#7f8c8d;'>" + node.title.replace(/\\n/g, "<br><br>");
                        overlay.style.display = "block";
                    }
                }
                
                network.on("click", function (params) {
                    if(params.nodes.length > 0) {
                        showTooltip(params.nodes[0]);
                    } else {
                        overlay.style.display = "none";
                    }
                });
                
                network.on("hoverNode", function (params) {
                    showTooltip(params.node);
                });
                
                closeBtn.onclick = function() {
                    overlay.style.display = "none";
                };
            }
        }, 200);
        
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
    
    with open(output_path, "r", encoding="utf-8") as f:
        html = f.read()
        
    if "</body>" in html:
        html = html.replace("</body>", f"{custom_css_js}</body>")
    else:
        html += custom_css_js
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
