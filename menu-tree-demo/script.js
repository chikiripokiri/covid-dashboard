document.addEventListener('DOMContentLoaded', () => {
    const menuInput = document.getElementById('menu-input');
    const generateBtn = document.getElementById('generate-btn');
    const downloadBtn = document.getElementById('download-btn');
    const svgContainer = document.getElementById('svg-container');

    // Configuration for tree layout
    const config = {
        nodeWidth: 150,
        nodeHeight: 50,
        horizontalGap: 50,
        verticalGap: 80,
        fontSize: 14,
        fontFamily: 'Inter, sans-serif',
        rectFill: '#ffffff',
        rectStroke: '#e2e8f0',
        textColor: '#0f172a',
        lineColor: '#94a3b8'
    };

    // Initial render
    generateTree();

    generateBtn.addEventListener('click', generateTree);
    downloadBtn.addEventListener('click', downloadSVG);

    function generateTree() {
        try {
            const data = JSON.parse(menuInput.value);
            svgContainer.innerHTML = ''; // Clear existing

            // Calculate positions
            const treeLayout = calculateLayout(data);

            // Create SVG
            const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.setAttribute("width", treeLayout.width + 100); // Add padding
            svg.setAttribute("height", treeLayout.height + 100);
            svg.setAttribute("viewBox", `-50 -50 ${treeLayout.width + 100} ${treeLayout.height + 100}`);
            svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");

            // Draw connections first (so they are behind nodes)
            drawConnections(svg, treeLayout.nodes);

            // Draw nodes
            drawNodes(svg, treeLayout.nodes);

            svgContainer.appendChild(svg);
        } catch (e) {
            alert('Invalid JSON format. Please check your input.');
            console.error(e);
        }
    }

    function calculateLayout(rootData) {
        let maxDepth = 0;
        let idCounter = 0;
        const nodes = [];

        function traverse(node, depth, parentId = null) {
            const id = idCounter++;
            const currentNode = {
                id,
                parentId,
                label: node.label,
                children: [],
                depth,
                x: 0,
                y: depth * (config.nodeHeight + config.verticalGap)
            };
            nodes.push(currentNode);
            maxDepth = Math.max(maxDepth, depth);

            if (node.children && node.children.length > 0) {
                node.children.forEach(child => {
                    const childNode = traverse(child, depth + 1, id);
                    currentNode.children.push(childNode);
                });
            }
            return currentNode;
        }

        const rootNode = traverse(rootData, 0);

        // Assign horizontal positions (simple algorithm)
        // We need to ensure nodes don't overlap. 
        // A simple approach: In-order traversal to assign X based on "next available X" per depth?? 
        // Easier: Recursive width calculation.

        function calculateWidth(node) {
            if (node.children.length === 0) {
                node.width = config.nodeWidth;
                return node.width;
            }
            let childrenWidth = 0;
            node.children.forEach((child, index) => {
                childrenWidth += calculateWidth(child);
                if (index < node.children.length - 1) {
                    childrenWidth += config.horizontalGap;
                }
            });
            node.width = childrenWidth;
            return Math.max(config.nodeWidth, childrenWidth);
        }

        calculateWidth(rootNode);

        function assignPositions(node, startX) {
            // center the node within its allocated width
            node.x = startX + (node.width / 2) - (config.nodeWidth / 2);

            let currentX = startX;
            node.children.forEach((child, index) => {
                assignPositions(child, currentX);
                currentX += child.width + config.horizontalGap;
            });
        }

        assignPositions(rootNode, 0);

        // Find total dimensions
        const maxX = Math.max(...nodes.map(n => n.x + config.nodeWidth));
        const maxY = Math.max(...nodes.map(n => n.y + config.nodeHeight));

        return { width: maxX, height: maxY, nodes };
    }

    function drawConnections(svg, nodes) {
        nodes.forEach(node => {
            if (node.parentId !== null) {
                const parent = nodes.find(n => n.id === node.parentId);
                const path = document.createElementNS("http://www.w3.org/2000/svg", "path");

                // Draw elbow connector
                const startX = parent.x + (config.nodeWidth / 2);
                const startY = parent.y + config.nodeHeight;
                const endX = node.x + (config.nodeWidth / 2);
                const endY = node.y;

                // Midpoint for vertical line
                const midY = startY + (endY - startY) / 2;

                const d = `M ${startX} ${startY} V ${midY} H ${endX} V ${endY}`;

                path.setAttribute("d", d);
                path.setAttribute("stroke", config.lineColor);
                path.setAttribute("stroke-width", "2");
                path.setAttribute("fill", "none");
                svg.appendChild(path);
            }
        });
    }

    function drawNodes(svg, nodes) {
        nodes.forEach(node => {
            const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
            g.setAttribute("transform", `translate(${node.x}, ${node.y})`);

            // Rectangle
            const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
            rect.setAttribute("width", config.nodeWidth);
            rect.setAttribute("height", config.nodeHeight);
            rect.setAttribute("rx", "6");
            rect.setAttribute("fill", config.rectFill);
            rect.setAttribute("stroke", config.rectStroke);
            rect.setAttribute("stroke-width", "1");
            // Add shadow filter (simplified as fake shadow for now or just stick to clean border)

            // Label
            const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
            text.setAttribute("x", config.nodeWidth / 2);
            text.setAttribute("y", config.nodeHeight / 2);
            text.setAttribute("dy", "0.3em"); // Vertical center adjustment
            text.setAttribute("text-anchor", "middle");
            text.setAttribute("fill", config.textColor);
            text.setAttribute("font-family", config.fontFamily);
            text.setAttribute("font-size", config.fontSize);
            text.setAttribute("font-weight", "500");
            text.textContent = node.label;

            g.appendChild(rect);
            g.appendChild(text);
            svg.appendChild(g);
        });
    }

    function downloadSVG() {
        const svg = svgContainer.querySelector('svg');
        if (!svg) return;

        const serializer = new XMLSerializer();
        let source = serializer.serializeToString(svg);

        // Add namespaces
        if (!source.match(/^<svg[^>]+xmlns="http\:\/\/www\.w3\.org\/2000\/svg"/)) {
            source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
        }
        if (!source.match(/^<svg[^>]+xmlns:xlink/)) {
            source = source.replace(/^<svg/, '<svg xmlns:xlink="http://www.w3.org/1999/xlink"');
        }

        // Add XML declaration
        source = '<?xml version="1.0" standalone="no"?>\r\n' + source;

        const url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(source);

        const downloadLink = document.createElement("a");
        downloadLink.href = url;
        downloadLink.download = "menu-tree.svg";
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
    }
});
