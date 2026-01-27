#include <bits/stdc++.h>
using namespace std;

int N, M, H;
vector<int> A;
vector<vector<int>> adj;

// Select roots so that every node is within distance <= H of some root.
// Greedy: repeatedly choose the uncovered vertex with the smallest A as a new root.
vector<int> select_roots() {
    const int INF = 1e9;
    vector<int> cover_dist(N, INF);
    vector<int> isRoot(N, 0);
    auto bfs_update = [&](int r) {
        vector<int> dist(N, -1);
        queue<int> q;
        dist[r] = 0;
        q.push(r);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            int d = dist[u];
            if (d < cover_dist[u]) cover_dist[u] = d;
            if (d == H) continue;
            for (int v : adj[u]) {
                if (dist[v] == -1) {
                    dist[v] = d + 1;
                    q.push(v);
                }
            }
        }
    };
    while (true) {
        int best = -1;
        int bestA = INT_MAX;
        for (int v = 0; v < N; v++) {
            if (cover_dist[v] > H) {
                if (A[v] < bestA) {
                    bestA = A[v];
                    best = v;
                }
            }
        }
        if (best == -1) break;
        isRoot[best] = 1;
        bfs_update(best);
    }
    vector<int> roots;
    for (int i = 0; i < N; i++) if (isRoot[i]) roots.push_back(i);
    if (roots.empty()) {
        // Fallback: pick the smallest A as a root
        int best = min_element(A.begin(), A.end()) - A.begin();
        roots.push_back(best);
    }
    return roots;
}

// Build initial forest by multi-source BFS from roots with depth limit H
void build_forest(const vector<int>& roots, vector<int>& parent, vector<int>& depth) {
    const int INF = 1e9;
    parent.assign(N, -2);
    depth.assign(N, INF);
    queue<int> q;
    for (int r : roots) {
        parent[r] = -1;
        depth[r] = 0;
        q.push(r);
    }
    while (!q.empty()) {
        int u = q.front(); q.pop();
        int d = depth[u];
        if (d == H) continue;
        for (int v : adj[u]) {
            if (depth[v] == INF) {
                depth[v] = d + 1;
                parent[v] = u;
                q.push(v);
            }
        }
    }
    // Fallback: any unvisited node becomes a root
    for (int i = 0; i < N; i++) {
        if (parent[i] == -2) {
            parent[i] = -1;
            depth[i] = 0;
        }
    }
}

void build_children(const vector<int>& parent, vector<vector<int>>& children) {
    children.assign(N, {});
    for (int v = 0; v < N; v++) {
        int p = parent[v];
        if (p != -1) children[p].push_back(v);
    }
}

// DFS to compute tin/tout, subtree sums and min slack
void compute_metrics(const vector<vector<int>>& children, const vector<int>& depth,
                     vector<int>& tin, vector<int>& tout,
                     vector<long long>& sumA_sub, vector<int>& minSlack_sub) {
    tin.assign(N, -1);
    tout.assign(N, -1);
    sumA_sub.assign(N, 0);
    minSlack_sub.assign(N, INT_MAX);
    vector<int> slack(N);
    for (int i = 0; i < N; i++) slack[i] = H - depth[i];

    int timer = 0;
    function<void(int)> dfs = [&](int u) {
        tin[u] = timer++;
        long long sumA = A[u];
        int minS = slack[u];
        for (int c : children[u]) {
            dfs(c);
            sumA += sumA_sub[c];
            minS = min(minS, minSlack_sub[c]);
        }
        sumA_sub[u] = sumA;
        minSlack_sub[u] = minS;
        tout[u] = timer;
    };

    for (int i = 0; i < N; i++) {
        if (children[i].empty() && tin[i] != -1) continue;
    }
    for (int i = 0; i < N; i++) {
        if (tin[i] == -1) {
            // if node has parent == -1 (root) it will be discovered; if it's not root but not visited yet due to ordering, still safe
            // We need to start DFS from actual roots to cover whole forest
            // Identify roots by lack of parent; We'll pass children info only, so identify roots: no parent if not present as a child of anyone
            // Easier: find nodes with no parent by checking if they are never a child.
            // But we don't have parent here; We'll rely on the property that nodes with no parent appear at top; build an auxiliary root list
            // However to avoid extra input, we run dfs starting at nodes that are not yet visited and treat it as roots.
            dfs(i);
        }
    }
}

void inc_depth_subtree(int u, const vector<vector<int>>& children, vector<int>& depth) {
    depth[u]++;
    for (int c : children[u]) inc_depth_subtree(c, children, depth);
}

// Improvement: push subtrees deeper by reparenting to same-depth neighbor outside subtree
void improve_forest(vector<int>& parent, vector<int>& depth) {
    vector<vector<int>> children;
    build_children(parent, children);

    int max_iters = 4000; // cap to ensure time safety
    for (int iter = 0; iter < max_iters; iter++) {
        vector<int> tin, tout;
        vector<long long> sumA_sub;
        vector<int> minSlack_sub;
        // Ensure depths are valid (<= H)
        bool ok = true;
        for (int i = 0; i < N; i++) {
            if (depth[i] < 0 || depth[i] > H) { ok = false; break; }
        }
        if (!ok) break;

        // Compute metrics
        // We need to run DFS from real roots to assign correct tin/tout for subtree checks.
        // Identify roots: parent == -1
        vector<int> roots;
        roots.reserve(N);
        for (int i = 0; i < N; i++) if (parent[i] == -1) roots.push_back(i);

        tin.assign(N, -1);
        tout.assign(N, -1);
        sumA_sub.assign(N, 0);
        minSlack_sub.assign(N, INT_MAX);
        vector<int> slack(N);
        for (int i = 0; i < N; i++) slack[i] = H - depth[i];

        int timer = 0;
        function<void(int)> dfs = [&](int u) {
            tin[u] = timer++;
            long long sumA = A[u];
            int minS = slack[u];
            for (int c : children[u]) {
                dfs(c);
                sumA += sumA_sub[c];
                minS = min(minS, minSlack_sub[c]);
            }
            sumA_sub[u] = sumA;
            minSlack_sub[u] = minS;
            tout[u] = timer;
        };
        for (int r : roots) dfs(r);

        // Find best candidate
        long long bestGain = -1;
        int bestU = -1, bestW = -1;
        for (int u = 0; u < N; u++) {
            if (minSlack_sub[u] < 1) continue;
            int d = depth[u];
            int candW = -1;
            for (int w : adj[u]) {
                if (depth[w] == d) {
                    if (!(tin[u] <= tin[w] && tin[w] < tout[u])) {
                        candW = w;
                        break;
                    }
                }
            }
            if (candW == -1) continue;
            long long gain = sumA_sub[u];
            if (gain > bestGain) {
                bestGain = gain;
                bestU = u;
                bestW = candW;
            }
        }

        if (bestU == -1) break; // no improvement possible

        // Apply shift: reparent bestU to bestW and increment depth of its subtree
        parent[bestU] = bestW;
        // Increase depth for subtree of bestU using current children list (before rebuild)
        inc_depth_subtree(bestU, children, depth);

        // Rebuild children for next iteration
        build_children(parent, children);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N >> M >> H)) {
        return 0;
    }
    A.resize(N);
    for (int i = 0; i < N; i++) cin >> A[i];
    adj.assign(N, {});
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    // Read coordinates (unused)
    for (int i = 0; i < N; i++) {
        int x, y;
        cin >> x >> y;
    }

    vector<int> roots = select_roots();

    vector<int> parent, depth;
    build_forest(roots, parent, depth);

    improve_forest(parent, depth);

    for (int i = 0; i < N; i++) {
        if (i) cout << ' ';
        cout << parent[i];
    }
    cout << '\n';
    return 0;
}