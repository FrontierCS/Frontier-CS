#include <bits/stdc++.h>
using namespace std;

static const int MAX_STEPS = 20000;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<int> cur(n), target(n);
    for (int i = 0; i < n; i++) cin >> cur[i];
    for (int i = 0; i < n; i++) cin >> target[i];

    vector<vector<int>> adj(n);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<vector<int>> states;
    states.push_back(cur);

    auto push_state = [&](const vector<int>& nxt) {
        if (nxt == cur) return;
        cur = nxt;
        states.push_back(cur);
    };

    // Find connected components
    vector<int> compId(n, -1);
    vector<vector<int>> comps;
    int cid = 0;
    for (int i = 0; i < n; i++) {
        if (compId[i] != -1) continue;
        queue<int> q;
        q.push(i);
        compId[i] = cid;
        comps.push_back({});
        comps.back().push_back(i);
        while (!q.empty()) {
            int v = q.front(); q.pop();
            for (int to : adj[v]) {
                if (compId[to] == -1) {
                    compId[to] = cid;
                    q.push(to);
                    comps.back().push_back(to);
                }
            }
        }
        cid++;
    }

    auto flood_uniform = [&](const vector<int>& nodes, int color) {
        // Iteratively expand 'color' to all nodes
        for (int iter = 0; iter < n; iter++) {
            bool done = true;
            for (int v : nodes) if (cur[v] != color) { done = false; break; }
            if (done) return;

            vector<int> nxt = cur;
            bool changed = false;
            for (int v : nodes) {
                if (cur[v] == color) continue;
                bool has = false;
                for (int u : adj[v]) {
                    if (cur[u] == color) { has = true; break; }
                }
                if (has) {
                    nxt[v] = color;
                    changed = true;
                }
            }
            if (!changed) return; // should not happen if solvable
            push_state(nxt);
            if ((int)states.size() - 1 > MAX_STEPS) return;
        }
    };

    auto solve_worm = [&](const vector<int>& nodes) {
        vector<char> inComp(n, 0);
        for (int v : nodes) inComp[v] = 1;

        // Build a BFS spanning tree for leaf removals
        vector<vector<int>> treeAdj(n);
        vector<int> par(n, -1);
        queue<int> q;
        int root = nodes[0];
        par[root] = root;
        q.push(root);
        while (!q.empty()) {
            int v = q.front(); q.pop();
            for (int to : adj[v]) {
                if (!inComp[to]) continue;
                if (par[to] != -1) continue;
                par[to] = v;
                treeAdj[v].push_back(to);
                treeAdj[to].push_back(v);
                q.push(to);
            }
        }

        vector<char> alive(n, 0);
        for (int v : nodes) alive[v] = 1;
        int aliveCount = (int)nodes.size();

        vector<int> deg(n, 0);
        for (int v : nodes) deg[v] = (int)treeAdj[v].size();

        auto alive_tree_neighbor = [&](int v) -> int {
            for (int u : treeAdj[v]) if (alive[u]) return u;
            return -1;
        };

        // Initialize worm (trail=0, head=1) on an edge with different colors.
        int trail = -1, head = -1;
        for (int v : nodes) {
            for (int to : adj[v]) {
                if (!inComp[to]) continue;
                if (cur[v] == cur[to]) continue;
                int a = v, b = to;
                if (cur[a] == 0 && cur[b] == 1) { trail = a; head = b; }
                else if (cur[a] == 1 && cur[b] == 0) { trail = b; head = a; }
                if (trail != -1) break;
            }
            if (trail != -1) break;
        }

        // If for some reason not found (shouldn't if target uses both colors), abort.
        if (trail == -1 || head == -1) return;

        auto move_to = [&](int nxt) {
            // Move worm head from 'head' to 'nxt' (neighbor), maintaining opposite colors
            vector<int> nextState = cur;
            if (nxt == trail) {
                // swap head and trail
                nextState[trail] = cur[head];
                nextState[head] = cur[trail];
                push_state(nextState);
                int oldTrail = trail;
                trail = head;
                head = oldTrail;
            } else {
                nextState[nxt] = cur[head];
                nextState[head] = cur[trail];
                push_state(nextState);
                trail = head;
                head = nxt;
            }
        };

        auto move_head_to = [&](int tgt) {
            if (head == tgt) return;
            vector<int> parent(n, -1);
            deque<int> dq;
            parent[head] = head;
            dq.push_back(head);
            while (!dq.empty() && parent[tgt] == -1) {
                int v = dq.front(); dq.pop_front();
                for (int to : adj[v]) {
                    if (!alive[to]) continue;
                    if (parent[to] != -1) continue;
                    parent[to] = v;
                    dq.push_back(to);
                }
            }
            if (parent[tgt] == -1) return; // should not happen
            vector<int> path;
            int x = tgt;
            while (x != head) {
                path.push_back(x);
                x = parent[x];
            }
            reverse(path.begin(), path.end());
            for (int nx : path) {
                move_to(nx);
                if ((int)states.size() - 1 > MAX_STEPS) return;
            }
        };

        auto remove_node = [&](int v) {
            alive[v] = 0;
            aliveCount--;
            for (int u : treeAdj[v]) if (alive[u]) deg[u]--;
            deg[v] = 0;
        };

        while (aliveCount > 2 && (int)states.size() - 1 <= MAX_STEPS) {
            // Prefer removing correct leaves not in worm endpoints without any step.
            int freeLeaf = -1;
            for (int v : nodes) {
                if (!alive[v]) continue;
                if (v == head || v == trail) continue;
                if (deg[v] == 1 && cur[v] == target[v]) { freeLeaf = v; break; }
            }
            if (freeLeaf != -1) {
                remove_node(freeLeaf);
                continue;
            }

            // Compute distances from current head within alive subgraph (for picking a closer leaf parent)
            vector<int> dist(n, -1);
            deque<int> dq;
            dist[head] = 0;
            dq.push_back(head);
            while (!dq.empty()) {
                int v = dq.front(); dq.pop_front();
                for (int to : adj[v]) {
                    if (!alive[to]) continue;
                    if (dist[to] != -1) continue;
                    dist[to] = dist[v] + 1;
                    dq.push_back(to);
                }
            }

            int bestLeaf = -1;
            int bestParent = -1;
            int bestD = INT_MAX;

            for (int v : nodes) {
                if (!alive[v]) continue;
                if (v == head || v == trail) continue;
                if (deg[v] != 1) continue;
                int p = alive_tree_neighbor(v);
                if (p == -1) continue;
                int d = dist[p];
                if (d == -1) continue;
                // Prefer smaller distance; tie-break by leaf index
                if (d < bestD) {
                    bestD = d;
                    bestLeaf = v;
                    bestParent = p;
                }
            }

            if (bestLeaf == -1) break; // should not happen

            int v = bestLeaf;
            int desired = target[v];

            if (cur[v] == desired) {
                remove_node(v);
                continue;
            }

            // Try direct copy from any neighbor (fixed or alive) that already has desired color
            int directFrom = -1;
            for (int u : adj[v]) {
                if (cur[u] == desired) { directFrom = u; break; }
            }
            if (directFrom != -1) {
                vector<int> nxt = cur;
                nxt[v] = cur[directFrom];
                push_state(nxt);
                if ((int)states.size() - 1 > MAX_STEPS) return;
                remove_node(v);
                continue;
            }

            int p = bestParent;

            if (desired == 1) {
                if (cur[p] != 1) move_head_to(p);
                // Now p should be 1 (at least via head being there)
                if (cur[v] != 1) {
                    vector<int> nxt = cur;
                    nxt[v] = 1;
                    push_state(nxt);
                    if ((int)states.size() - 1 > MAX_STEPS) return;
                }
                remove_node(v);
            } else { // desired == 0
                if (cur[p] == 0) {
                    vector<int> nxt = cur;
                    nxt[v] = 0;
                    push_state(nxt);
                    if ((int)states.size() - 1 > MAX_STEPS) return;
                    remove_node(v);
                } else {
                    // Make p become 0 by ensuring head at p then moving head away one step.
                    move_head_to(p);
                    if ((int)states.size() - 1 > MAX_STEPS) return;

                    int qn = -1;
                    for (int u : treeAdj[p]) {
                        if (alive[u] && u != v) { qn = u; break; }
                    }
                    if (qn == -1) qn = v; // fallback

                    move_to(qn); // p becomes 0 (old head)
                    if ((int)states.size() - 1 > MAX_STEPS) return;

                    if (cur[v] != 0) {
                        vector<int> nxt = cur;
                        nxt[v] = 0;
                        push_state(nxt);
                        if ((int)states.size() - 1 > MAX_STEPS) return;
                    }
                    remove_node(v);
                }
            }
        }

        if ((int)states.size() - 1 > MAX_STEPS) return;

        // Handle last 1 or 2 alive nodes
        vector<int> last;
        last.reserve(2);
        for (int v : nodes) if (alive[v]) last.push_back(v);

        if (last.size() == 1) {
            // Should already match target if solvable in this component
            // Can't change an isolated node in final phase anyway.
            return;
        }

        if (last.size() == 2) {
            int a = last[0], b = last[1];
            if (cur[a] == target[a] && cur[b] == target[b]) return;

            // We can set both in one step if each desired is one of the two current colors.
            if ((target[a] == cur[a] || target[a] == cur[b]) &&
                (target[b] == cur[b] || target[b] == cur[a])) {
                vector<int> nxt = cur;
                nxt[a] = target[a];
                nxt[b] = target[b];
                push_state(nxt);
            } else {
                // Fallback: try two steps via copying if possible (should not be needed)
                // Step 1: if target[a] == cur[b], set a; else if target[b] == cur[a], set b
                vector<int> nxt = cur;
                bool did = false;
                if (target[a] == cur[b] && target[a] != cur[a]) { nxt[a] = cur[b]; did = true; }
                if (target[b] == cur[a] && target[b] != cur[b]) { nxt[b] = cur[a]; did = true; }
                if (did) push_state(nxt);

                if (cur[a] != target[a] || cur[b] != target[b]) {
                    vector<int> nxt2 = cur;
                    if (target[a] == cur[b]) nxt2[a] = cur[b];
                    if (target[b] == cur[a]) nxt2[b] = cur[a];
                    push_state(nxt2);
                }
            }
        }
    };

    for (const auto& nodes : comps) {
        bool allOk = true;
        int has0 = 0, has1 = 0;
        for (int v : nodes) {
            if (cur[v] != target[v]) allOk = false;
            if (target[v] == 0) has0 = 1;
            else has1 = 1;
        }
        if (allOk) continue;

        if (has0 + has1 == 1) {
            int c = has0 ? 0 : 1;
            flood_uniform(nodes, c);
        } else {
            solve_worm(nodes);
        }
        if ((int)states.size() - 1 > MAX_STEPS) break;
    }

    // Ensure last state equals target; if not, try a final direct step where possible (best-effort)
    if (cur != target && (int)states.size() - 1 < MAX_STEPS) {
        vector<int> nxt = cur;
        bool changed = false;
        for (int v = 0; v < n; v++) {
            if (nxt[v] == target[v]) continue;
            bool ok = false;
            if (cur[v] == target[v]) ok = true;
            for (int u : adj[v]) if (cur[u] == target[v]) { ok = true; break; }
            if (ok) { nxt[v] = target[v]; changed = true; }
        }
        if (changed) push_state(nxt);
    }

    int k = (int)states.size() - 1;
    if (k > MAX_STEPS) {
        // Truncate to satisfy hard limit (should not happen); keep valid prefix.
        k = MAX_STEPS;
        states.resize(MAX_STEPS + 1);
    }

    cout << k << "\n";
    for (int i = 0; i <= k; i++) {
        for (int j = 0; j < n; j++) {
            if (j) cout << ' ';
            cout << states[i][j];
        }
        cout << "\n";
    }

    return 0;
}