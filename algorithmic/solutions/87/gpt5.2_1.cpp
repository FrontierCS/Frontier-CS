#include <bits/stdc++.h>
using namespace std;

struct OrEdge {
    int a, b; // a has color 0, b has color 1
};

static void applyStep(int n, vector<int>& cur, vector<vector<int>>& states, const vector<int>& act) {
    vector<int> nxt = cur;
    for (int i = 0; i < n; i++) {
        if (act[i] != -1) nxt[i] = cur[act[i]];
    }
    cur.swap(nxt);
    states.push_back(cur);
}

static inline int idOf(int n, int u, int v) { return u * n + v; }

static void bfsOriented(
    int n,
    const vector<vector<int>>& tAdj,
    const vector<char>& active,
    OrEdge start,
    vector<int>& dist,
    vector<int>& parent
) {
    int NN = n * n;
    dist.assign(NN, -1);
    parent.assign(NN, -1);

    int s = idOf(n, start.a, start.b);
    queue<int> q;
    dist[s] = 0;
    parent[s] = s;
    q.push(s);

    auto push = [&](int from, int to) {
        if (dist[to] != -1) return;
        dist[to] = dist[from] + 1;
        parent[to] = from;
        q.push(to);
    };

    while (!q.empty()) {
        int x = q.front(); q.pop();
        int u = x / n;
        int v = x % n;
        if (!active[u] || !active[v]) continue;

        // reversal (v,u)
        int rev = idOf(n, v, u);
        push(x, rev);

        // forward: (v,w) for w neighbor of v, w!=u
        for (int w : tAdj[v]) {
            if (!active[w] || w == u) continue;
            int to = idOf(n, v, w);
            push(x, to);
        }

        // backward: (w,u) for w neighbor of u, w!=v
        for (int w : tAdj[u]) {
            if (!active[w] || w == v) continue;
            int to = idOf(n, w, u);
            push(x, to);
        }
    }
}

static void applyTransition(
    int n,
    vector<int>& cur,
    vector<vector<int>>& states,
    OrEdge from,
    OrEdge to
) {
    vector<int> act(n, -1);

    int u = from.a, v = from.b;
    int a = to.a, b = to.b;

    if (a == v && b == u) {
        // reversal
        act[u] = v;
        act[v] = u;
    } else if (a == v) {
        // forward: (u,v) -> (v,w)
        int w = b;
        act[v] = u;
        act[w] = v;
    } else if (b == u) {
        // backward: (u,v) -> (w,u)
        int w = a;
        act[u] = v;
        act[w] = u;
    } else {
        // Should not happen; fallback do nothing (will likely fail later if reached)
        // Keep as no-op to avoid UB.
    }
    applyStep(n, cur, states, act);
}

static int uniqueActiveNeighbor(int v, const vector<vector<int>>& tAdj, const vector<char>& active) {
    for (int u : tAdj[v]) if (active[u]) return u;
    return -1;
}

static void solveComponent(
    int n,
    const vector<int>& target,
    const vector<vector<int>>& adj,
    const vector<int>& compNodes,
    vector<int>& cur,
    vector<vector<int>>& states
) {
    int sz = (int)compNodes.size();
    if (sz <= 1) return;

    vector<char> inComp(n, 0);
    for (int v : compNodes) inComp[v] = 1;

    bool has0 = false, has1 = false;
    bool allMatch = true;
    for (int v : compNodes) {
        has0 |= (cur[v] == 0);
        has1 |= (cur[v] == 1);
        if (cur[v] != target[v]) allMatch = false;
    }
    if (allMatch) return;
    if (!has0 || !has1) {
        // Component is monochrome; cannot change to include absent color.
        // Guaranteed solvable => target must already match; if not, do nothing.
        return;
    }

    // Build spanning tree adjacency for this component.
    vector<vector<int>> tAdj(n);
    vector<char> vis(n, 0);
    queue<int> q;
    int root = compNodes[0];
    vis[root] = 1;
    q.push(root);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : adj[u]) {
            if (!inComp[v] || vis[v]) continue;
            vis[v] = 1;
            tAdj[u].push_back(v);
            tAdj[v].push_back(u);
            q.push(v);
        }
    }

    // Active set and degrees in active tree.
    vector<char> active(n, 0);
    vector<int> deg(n, 0);
    for (int v : compNodes) active[v] = 1;
    for (int v : compNodes) {
        int d = 0;
        for (int u : tAdj[v]) if (active[u]) d++;
        deg[v] = d;
    }
    int activeCount = sz;

    // Find initial oriented edge with different colors.
    OrEdge current{-1, -1};
    for (int u : compNodes) {
        for (int v : tAdj[u]) {
            if (u < v && cur[u] != cur[v]) {
                if (cur[u] == 0) current = {u, v};
                else current = {v, u};
                break;
            }
        }
        if (current.a != -1) break;
    }
    if (current.a == -1) return; // should not happen

    auto finishLastTwo = [&](int a, int b) {
        if (cur[a] == target[a] && cur[b] == target[b]) return;

        vector<int> act(n, -1);

        if (target[a] == target[b]) {
            int t = target[a];
            if (cur[a] != t && cur[b] == t) act[a] = b;
            else if (cur[b] != t && cur[a] == t) act[b] = a;
            else if (cur[a] != t && cur[b] != t) {
                // they differ, so one has t and one doesn't; handled above
                // fallback: make both copy b (arbitrary) then fix; but should not be needed.
                act[a] = b;
            }
        } else {
            // targets differ; with two nodes, must be either already correct or swap.
            if (cur[a] == target[b] && cur[b] == target[a]) {
                act[a] = b;
                act[b] = a;
            } else {
                // Should not happen; try to fix individually if possible
                if (cur[a] != target[a]) act[a] = b;
                if (cur[b] != target[b]) act[b] = a;
            }
        }
        applyStep(n, cur, states, act);
    };

    if (activeCount == 2) {
        int a = compNodes[0], b = compNodes[1];
        finishLastTwo(a, b);
        return;
    }

    vector<int> dist, parent;

    while (activeCount > 2) {
        bfsOriented(n, tAdj, active, current, dist, parent);

        int bestL = -1, bestP = -1;
        OrEdge desired{-1, -1};
        int bestD = INT_MAX;

        for (int L : compNodes) {
            if (!active[L] || deg[L] != 1) continue;
            int P = uniqueActiveNeighbor(L, tAdj, active);
            if (P == -1) continue;

            OrEdge want;
            if (target[L] == 1) want = {P, L};
            else want = {L, P};

            int tid = idOf(n, want.a, want.b);
            int d = dist[tid];
            if (d == -1) continue;

            if (d < bestD) {
                bestD = d;
                bestL = L;
                bestP = P;
                desired = want;
            }
        }

        if (bestL == -1) break; // should not happen in a valid tree with >2 vertices

        // Choose X: active neighbor of P excluding L with highest active degree.
        int X = -1, bestDeg = -1;
        for (int u : tAdj[bestP]) {
            if (!active[u] || u == bestL) continue;
            if (deg[u] > bestDeg) {
                bestDeg = deg[u];
                X = u;
            }
        }
        if (X == -1) {
            // Should not happen when activeCount > 2
            break;
        }

        // Reconstruct path of oriented edges from current to desired.
        int startId = idOf(n, current.a, current.b);
        int targetId = idOf(n, desired.a, desired.b);
        vector<int> path;
        if (parent[targetId] == -1) {
            // unreachable; should not happen
            break;
        }
        int x = targetId;
        while (x != startId) {
            path.push_back(x);
            x = parent[x];
        }
        path.push_back(startId);
        reverse(path.begin(), path.end());

        // Apply transitions along path.
        for (int i = 0; i + 1 < (int)path.size(); i++) {
            int s = path[i], t = path[i + 1];
            OrEdge from{s / n, s % n};
            OrEdge to{t / n, t % n};
            applyTransition(n, cur, states, from, to);
            current = to;
        }

        // Now current is desired. Detach leaf bestL, keep leaf fixed.
        // actions: X copies P, P copies L
        vector<int> act(n, -1);
        act[X] = bestP;
        act[bestP] = bestL;
        applyStep(n, cur, states, act);

        // Update current oriented edge after detach
        if (target[bestL] == 1) current = {X, bestP};
        else current = {bestP, X};

        // Remove leaf from active set
        active[bestL] = 0;
        activeCount--;
        deg[bestP]--;
        deg[bestL] = 0;
    }

    // Finish last two active nodes
    vector<int> rem;
    rem.reserve(2);
    for (int v : compNodes) if (active[v]) rem.push_back(v);
    if ((int)rem.size() == 2) finishLastTwo(rem[0], rem[1]);
}

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

    // Find connected components
    vector<int> compId(n, -1);
    vector<vector<int>> comps;
    for (int i = 0; i < n; i++) {
        if (compId[i] != -1) continue;
        queue<int> q;
        q.push(i);
        compId[i] = (int)comps.size();
        comps.push_back({});
        comps.back().push_back(i);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (compId[v] != -1) continue;
                compId[v] = compId[i];
                comps.back().push_back(v);
                q.push(v);
            }
        }
    }

    vector<vector<int>> states;
    states.reserve(12000);
    states.push_back(cur);

    for (const auto& nodes : comps) {
        solveComponent(n, target, adj, nodes, cur, states);
    }

    // If any nodes still mismatch (shouldn't), attempt one last no-op.
    // (Do not add steps; sequence validity matters.)
    // Ensure within bounds (guaranteed by construction).
    int k = (int)states.size() - 1;
    cout << k << "\n";
    for (const auto& st : states) {
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << st[i];
        }
        cout << "\n";
    }
    return 0;
}