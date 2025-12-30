#include <bits/stdc++.h>
using namespace std;

static const int INF = 1e9;

vector<int> multi_source_bfs_dist(const vector<vector<int>>& g, const vector<int>& roots) {
    int N = g.size();
    vector<int> dist(N, INF);
    queue<int> q;
    for (int r : roots) {
        dist[r] = 0;
        q.push(r);
    }
    while (!q.empty()) {
        int v = q.front(); q.pop();
        for (int u : g[v]) {
            if (dist[u] > dist[v] + 1) {
                dist[u] = dist[v] + 1;
                q.push(u);
            }
        }
    }
    return dist;
}

pair<vector<int>, vector<int>> build_forest_from_roots(const vector<vector<int>>& g, const vector<int>& roots, int H) {
    int N = g.size();
    vector<int> parent(N, -2), depth(N, -1);
    queue<int> q;
    for (int r : roots) {
        parent[r] = -1;
        depth[r] = 0;
        q.push(r);
    }
    while (!q.empty()) {
        int v = q.front(); q.pop();
        if (depth[v] == H) continue;
        for (int u : g[v]) {
            if (depth[u] == -1) {
                parent[u] = v;
                depth[u] = depth[v] + 1;
                q.push(u);
            }
        }
    }
    for (int v = 0; v < N; v++) {
        if (parent[v] == -2) {
            parent[v] = -1;
            depth[v] = 0;
        }
    }
    return {parent, depth};
}

void prune_roots(vector<int>& roots, const vector<vector<int>>& g, int H) {
    if (roots.empty()) return;
    int N = g.size();
    vector<int> roots_copy = roots;
    bool changed = true;
    while (changed) {
        changed = false;
        if (roots.size() <= 1) break;
        vector<int> order(roots.size());
        iota(order.begin(), order.end(), 0);
        // Attempt to remove roots with higher A first requires A known; we'll reconstruct a comparator externally.
        // For simplicity, try in natural order; we'll still loop until convergence.
        for (int idx = 0; idx < (int)roots.size(); idx++) {
            if (roots.size() <= 1) break;
        }
        // Better: try each root; if removable, remove and restart
        for (int i = 0; i < (int)roots.size(); i++) {
            if (roots.size() <= 1) break;
            int r = roots[i];
            vector<int> cand;
            cand.reserve(roots.size() - 1);
            for (int j = 0; j < (int)roots.size(); j++) if (j != i) cand.push_back(roots[j]);
            if (cand.empty()) continue;
            vector<int> d = multi_source_bfs_dist(g, cand);
            int mx = -1;
            for (int v = 0; v < N; v++) mx = max(mx, d[v]);
            if (mx <= H) {
                roots.erase(roots.begin() + i);
                changed = true;
                break;
            }
        }
    }
}

struct TreeInfo {
    vector<vector<int>> children;
    vector<int> depth;
    vector<int> tin, tout;
    vector<long long> subSumA;
    vector<int> subMaxDepth;
    int timer;
};

void dfs_build(int u, const vector<vector<int>>& children, const vector<int>& A, TreeInfo& info) {
    info.tin[u] = info.timer++;
    info.subSumA[u] = A[u];
    int md = info.depth[u];
    for (int v : children[u]) {
        info.depth[v] = info.depth[u] + 1;
        dfs_build(v, children, A, info);
        info.subSumA[u] += info.subSumA[v];
        if (info.subMaxDepth[v] > md) md = info.subMaxDepth[v];
    }
    info.subMaxDepth[u] = md;
    info.tout[u] = info.timer++;
}

TreeInfo compute_tree_info(const vector<int>& parent, const vector<vector<int>>& g, const vector<int>& A) {
    int N = g.size();
    TreeInfo info;
    info.children.assign(N, {});
    info.depth.assign(N, 0);
    info.tin.assign(N, 0);
    info.tout.assign(N, 0);
    info.subSumA.assign(N, 0);
    info.subMaxDepth.assign(N, 0);
    info.timer = 0;
    for (int v = 0; v < N; v++) {
        int p = parent[v];
        if (p != -1) info.children[p].push_back(v);
    }
    for (int v = 0; v < N; v++) {
        if (parent[v] == -1) {
            info.depth[v] = 0;
            dfs_build(v, info.children, A, info);
        }
    }
    return info;
}

bool is_ancestor(int u, int v, const vector<int>& tin, const vector<int>& tout) {
    return tin[u] <= tin[v] && tout[v] <= tout[u];
}

void improve_forest(vector<int>& parent, const vector<vector<int>>& g, const vector<int>& A, int H, double time_limit_sec) {
    int N = g.size();
    auto start = chrono::steady_clock::now();
    int iter = 0;
    while (true) {
        TreeInfo info = compute_tree_info(parent, g, A);
        long long bestGain = 0;
        int bestV = -1, bestU = -1;
        for (int v = 0; v < N; v++) {
            for (int u : g[v]) {
                if (u == parent[v]) continue;
                // Avoid cycle: u must not be in v's subtree
                if (is_ancestor(v, u, info.tin, info.tout)) continue;
                int delta = info.depth[u] + 1 - info.depth[v];
                if (delta <= 0) continue;
                if (info.subMaxDepth[v] + delta <= H) {
                    long long gain = 1LL * delta * info.subSumA[v];
                    if (gain > bestGain) {
                        bestGain = gain;
                        bestV = v;
                        bestU = u;
                    }
                }
            }
        }
        if (bestGain <= 0) break;
        parent[bestV] = bestU;
        iter++;
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > time_limit_sec) break;
        if (iter > 2000) break;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M, H;
    if (!(cin >> N >> M >> H)) {
        return 0;
    }
    vector<int> A(N);
    for (int i = 0; i < N; i++) cin >> A[i];
    vector<vector<int>> g(N);
    for (int i = 0; i < M; i++) {
        int u, v; cin >> u >> v;
        g[u].push_back(v);
        g[v].push_back(u);
    }
    vector<int> xs(N), ys(N);
    for (int i = 0; i < N; i++) cin >> xs[i] >> ys[i];

    // Initial root selection: farthest-point sampling until max dist <= H
    vector<int> roots;
    int first = 0;
    for (int i = 1; i < N; i++) if (A[i] < A[first]) first = i;
    roots.push_back(first);
    while (true) {
        vector<int> dist = multi_source_bfs_dist(g, roots);
        int mx = -1;
        for (int v = 0; v < N; v++) mx = max(mx, dist[v]);
        if (mx <= H) break;
        int best = -1, bestA = INT_MAX, bestDeg = INT_MAX;
        for (int v = 0; v < N; v++) {
            if (dist[v] == mx) {
                int deg = (int)g[v].size();
                if (A[v] < bestA || (A[v] == bestA && deg < bestDeg)) {
                    bestA = A[v];
                    bestDeg = deg;
                    best = v;
                }
            }
        }
        if (best == -1) {
            // Fallback: pick any with maximal distance
            for (int v = 0; v < N; v++) if (dist[v] == mx) { best = v; break; }
        }
        if (best == -1) break;
        roots.push_back(best);
    }

    // Prune redundant roots
    prune_roots(roots, g, H);

    // Build initial forest
    auto forest = build_forest_from_roots(g, roots, H);
    vector<int> parent = forest.first;
    vector<int> depth = forest.second;

    // Local improvement
    improve_forest(parent, g, A, H, 1.7);

    // Output
    for (int i = 0; i < N; i++) {
        if (i) cout << ' ';
        cout << parent[i];
    }
    cout << '\n';
    return 0;
}