var ws = openWs();

var width = 960,
    height = 500;

var color = d3.scaleOrdinal(d3.schemeCategory20);

var cola = cola.d3adaptor(d3)
    .linkDistance(80)
    .avoidOverlaps(true)
    .handleDisconnected(false)
    .size([width, height]);

var svg = d3.select("#viz-view").append("svg")
    .attr("preserveAspectRatio", "xMinYMin meet")
    .attr("viewBox", "150 50 730 730");

d3.json("./data.json", function (error, graph) {

    graph.nodes.forEach(function (v) {
        v.width = v.network ? 150 : 95;
        v.height = 95;
    });

    graph.groups.forEach(function (g) {
        g.padding = 0.01;
    });
    cola
        .nodes(graph.nodes)
        .links(graph.links)
        .groups(graph.groups)
        .start(100, 0, 50, 50);

    var group = svg.selectAll(".group")
        .data(graph.groups)
        .enter().append("rect")
        .attr("rx", 8).attr("ry", 8)
        .attr("class", "group")
        .style("fill", function (d, i) {
            return color(i);
        });

    svg.selectAll(".wired-network-link")
        .data(graph.links.filter(function (el) {
            if (el.type && el.type === "wired-network") return el;
        }))
        .enter().append("line")
        .attr("class", "wired-network-link");

    svg.selectAll(".wireless-network-link")
        .data(graph.links.filter(function (el) {
            if (el.type && el.type === "wireless-network") return el;
        }))
        .enter().append("line")
        .attr("class", "wireless-network-link")
        .style("stroke-dasharray", ("5, 5"));

    svg.selectAll(".io-link")
        .data(graph.links.filter(function (el) {
            if (el.type && el.type === "io") return el;
        }))
        .enter().append("line")
        .attr("class", "io-link");

    var allLinks = svg.selectAll(".wired-network-link, .wireless-network-link, .io-link");

    var pad = 10;
    var node = svg.selectAll(".node")
        .data(graph.nodes)
        .enter().append("rect")
        .each(function (d) {
            var s = d3.select(this);
            if (!d.type) return;
            if (d.type === "motor") s.attr("class", "node physical-device");
            else s.attr("class", "node network-device");
        })
        .attr("width", function (d) {
            return d.width - 2 * pad;
        })
        .attr("height", function (d) {
            return d.height - 2 * pad;
        })
        .attr("rx", 5).attr("ry", 5)
        .call(cola.drag)
        .on('mouseup', function (d) {
            d.fixed = 0;
            cola.alpha(1); // fire it off again to satisfy gridify
        });

    var label = svg.selectAll(".label")
        .data(graph.nodes)
        .enter().append("text").attr("id", (function (d) {
            return d.id;
        }))
        .call(cola.drag);

    label.each(function (text) {
        var nodeData = getById(graph.nodes, text.id);
        if (nodeData == null)
            return;

        var svgText = d3.select(this);

        var tspan = svgText.append("tspan").text(nodeData.name).attr("class", "label");

        function appendNetworkEl(name, value) {
            svgText.append("tspan").text(name + ": ").attr("class", "var-label").attr("dy", 10).attr("x", text.bounds.x + 20);
            svgText.append("tspan").text(value).attr("class", "var-value " + name);
        }

        if (nodeData.network) {
            if (nodeData.network.ip) appendNetworkEl('IP', nodeData.network.ip);
            if (nodeData.network.mac) appendNetworkEl('MAC', nodeData.network.mac);
            if (nodeData.network.netmask) appendNetworkEl('Netmask', nodeData.network.netmask);
        }

        /* Monitoring variables is currently limited to PLCs, Motors and HMIs. */
        if (nodeData.type &&
            (nodeData.type === 'plc' || nodeData.type === 'motor' || nodeData.type === 'hmi')) {
            var varsText = svgText
                .append("tspan")
                .text("Variables")
                .attr("class", "var-label variables-link")
                .attr("dy", 10)
                .attr("x", text.bounds.x + 20);

            varsText.on("click", function () {
                updateVarsView(nodeData);
            });
        }

    });

    var subscribedTo = [];

    function updateVarsView(node) {
        var name = node.name;

        // Partition subscriptions
        // Add all devices to unsubscribe to array
        var unsub = subscribedTo.filter(function (el) {
            return el !== name;
        });

        // If we have devices to unsubscribe, send via ws
        if (unsub.length > 0) {
            ws.send(JSON.stringify({'unsubscribe': unsub}));
            // Update subscriptions (remove all unsubbed devices)
            subscribedTo = subscribedTo.filter(function (el) {
                return unsub.indexOf(el) === -1;
            });
        }

        // Subscribe to device if no corresponding subscription exists yet
        if (subscribedTo.indexOf(name) === -1) {
            ws.send(JSON.stringify({'subscribe': name}));
            subscribedTo.push(name);
        }

        /* Update header text. */
        var varsHead = document.getElementById('vars-head');
        if (varsHead)
            varsHead.innerText = name + " Variables";
        else
            console.warn('Could not update header of table, because element was not found.');

        var varsTbl = document.getElementById('vars-tbl');
        var oldVarsTblBodyRef = varsTbl.getElementsByTagName('tbody');
        if (oldVarsTblBodyRef.length > 0) {
            var oldVarsTblBody = oldVarsTblBodyRef[0];
            var newVarsTblBody = document.createElement('tbody');
            fetchTags(name, function () {
                if (this.readyState === 4) {
                    if (this.status === 200) {
                        JSON.parse(this.responseText).forEach(function (entry, idx) {
                            var tr = newVarsTblBody.insertRow();

                            function insertCell(val) {
                                var td = tr.insertCell();
                                td.appendChild(document.createTextNode(val));
                            }

                            function insertIdxTh() {
                                var th = document.createElement('th');
                                th.setAttribute('scope', 'row');
                                th.innerText = idx + 1;
                                tr.appendChild(th);
                            }

                            insertIdxTh();
                            insertCell(entry.name);
                            insertCell(entry.value);

                        });
                        /* Replace old content of variables table with new one. */
                        var parentNode = oldVarsTblBody.parentNode;
                        if (parentNode)
                            parentNode.replaceChild(newVarsTblBody, oldVarsTblBody);
                        else
                            console.warn('Could not replace variables table with new content!');
                    } else {
                        console.error(this.statusText);
                    }
                }
            });
        }
        else console.warn('Could not update variables table, because element was not found.');


        ws.onmessage = function (event) {
            var result = JSON.parse(event.data);
            if ('tag_change' in result) {
                var tagChange = result['tag_change'];
                for (var i = 0; i < varsTbl.rows.length; i++) {
                    var row = varsTbl.rows[i];
                    if (row.cells.length === 3) {
                        // Update cell only if value changed
                        if (row.cells[1].innerHTML === tagChange['name'] &&
                            row.cells[2].innerHTML !== tagChange['value'].toString()) {
                            row.cells[2].innerHTML = tagChange['value'];
                            flash(row);
                        }
                    }
                }
            }
        };

        function flash(el) {
            var cssBlink = "variable-blink";
            el.classList.add(cssBlink);
            setTimeout(function () {
                el.classList.remove(cssBlink);
            }, 100);
        }


    }

    var varLabel = svg.selectAll(".var-label");

    function getById(arr, id) {
        for (var d = 0, len = arr.length; d < len; d += 1) {
            if (arr[d].id === id) {
                return arr[d];
            }
        }
    }

    node.append("title")
        .text(function (d) {
            return d.name;
        });

    cola.on("tick", function () {
        allLinks.attr("x1", function (d) {
            return d.source.x;
        })
            .attr("y1", function (d) {
                return d.source.y;
            })
            .attr("x2", function (d) {
                return d.target.x;
            })
            .attr("y2", function (d) {
                return d.target.y;
            });

        node.attr("x", function (d) {
            return d.x - d.width / 2 + pad;
        })
            .attr("y", function (d) {
                return d.y - d.height / 2 + pad;
            });

        group.attr("x", function (d) {
            return d.bounds.x;
        })
            .attr("y", function (d) {
                return d.bounds.y;
            })
            .attr("width", function (d) {
                return d.bounds.width();
            })
            .attr("height", function (d) {
                return d.bounds.height();
            });

        label.attr("x", function (d) {
            return d.bounds.x + 20;
        })
            .attr("y", function (d) {
                return d.bounds.y + 30;
            });

        varLabel.attr("x", function (d) {
            return d.bounds.x + 20;
        })
    });
});

function fetchTags(name, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/api/v1/" + name, true);
    xhr.callback = callback;
    xhr.onerror = function (e) {
        console.error(xhr.statusText);
    };
    xhr.onload = function () {
        this.callback.apply(this, this.arguments);
    };
    xhr.send(null);
}


function openWs() {

    // Cf. https://stackoverflow.com/a/10418013/8516723
    function getWsLoc() {
        var loc = window.location, new_uri;
        var port = 8000;
        if (loc.protocol === "https:") {
            new_uri = "wss:";
        } else {
            new_uri = "ws:";
        }
        new_uri += "//" + loc.host + ":" + port;
        new_uri += "/";
        return new_uri;
    }

    return new WebSocket(getWsLoc());

}