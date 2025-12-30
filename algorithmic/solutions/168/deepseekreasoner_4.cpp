#include <bits/stdc++.h>
using namespace std;

const int MAX_N = 1000;
const int H = 10;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M >> H;
    vector<int> A(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    vector<pair<int, int>> edges(M);
    for (int i = 0; i < M; ++i) {
        cin >> edges[i].first >> edges[i].second;
    }
    vector<int> x(N), y(N);
    for (int i = 0; i < N; ++i) {
        cin >> x[i] >> y[i];
    }

    // Build adjacency list
    vector<vector<int>> adj(N);
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // For each vertex, compute list of vertices within distance H (BFS)
    // L[v] = list of (u, dist) sorted by (dist, u)
    vector<vector<pair<int, int>>> L(N);
    for (int v = 0; v < N; ++v) {
        queue<pair<int, int>> q; // (vertex, distance)
        vector<bool> visited(N, false);
        q.push({v, 0});
        visited[v] = true;
        while (!q.empty()) {
            auto [u, d] = q.front(); q.pop();
            if (d > H) continue;
            L[v].push_back({u, d});
            if (d == H) continue;
            for (int w : adj[u]) {
                if (!visited[w]) {
                    visited[w] = true;
                    q.push({w, d+1});
                }
            }
        }
        sort(L[v].begin(), L[v].end(),
             [](const pair<int,int> &a, const pair<int,int> &b) {
                 if (a.second != b.second) return a.second < b.second;
                 return a.first < b.first;
             });
    }

    // Initialization
    vector<bool> in_R(N, true);
    vector<int> idx(N, 0); // index in L[v] of current nearest root
    vector<vector<int>> dependents(N);
    for (int v = 0; v < N; ++v) {
        dependents[v].push_back(v);
    }
    long long total = 0;
    for (int v = 0; v < N; ++v) total += A[v]; // d=0 -> (0+1)*A

    // Greedy removal passes
    bool changed = true;
    while (changed) {
        changed = false;
        // Collect current roots
        vector<int> roots;
        for (int v = 0; v < N; ++v) if (in_R[v]) roots.push_back(v);
        // Sort by beauty descending (prefer to remove high beauty vertices first)
        sort(roots.begin(), roots.end(),
             [&](int a, int b) { return A[a] > A[b]; });

        for (int r : roots) {
            if (!in_R[r]) continue;
            // Try to remove r
            bool valid = true;
            long long gain = 0;
            vector<pair<int, int>> updates; // (v, new_idx)
            for (int v : dependents[r]) {
                int cur_idx = idx[v];
                // find next index in L[v] that is in R and not r
                int new_idx = cur_idx + 1;
                while (new_idx < (int)L[v].size() && !in_R[L[v][new_idx].first]) {
                    new_idx++;
                }
                if (new_idx == (int)L[v].size() || L[v][new_idx].second > H) {
                    valid = false;
                    break;
                }
                int old_d = L[v][cur_idx].second;
                int new_d = L[v][new_idx].second;
                gain += (long long)(new_d - old_d) * A[v];
                updates.emplace_back(v, new_idx);
            }
            if (valid && gain >= 0) {
                // Remove r
                in_R[r] = false;
                total += gain;
                for (auto &up : updates) {
                    int v = up.first;
                    int new_idx = up.second;
                    idx[v] = new_idx;
                    int new_root = L[v][new_idx].first;
                    dependents[new_root].push_back(v);
                }
                dependents[r].clear();
                changed = true;
            }
        }
    }

    // Now compute parent assignments using multi-source BFS with tie-breaking by root index
    vector<int> best_dist(N, H+1);
    vector<int> best_root(N, -1);
    vector<int> parent(N, -1);
    vector<vector<int>> bucket(H+1); // vertices at each distance
    for (int v = 0; v < N; ++v) {
        if (in_R[v]) {
            best_dist[v] = 0;
            best_root[v] = v;
            parent[v] = -1;
            bucket[0].push_back(v);
        }
    }
    for (int d = 0; d <= H; ++d) {
        for (int u : bucket[d]) {
            if (best_dist[u] != d) continue;
            for (int w : adj[u]) {
                int nd = d + 1;
                if (nd > H) continue;
                if (nd < best_dist[w] || (nd == best_dist[w] && best_root[u] < best_root[w])) {
                    best_dist[w] = nd;
                    best_root[w] = best_root[u];
                    parent[w] = u;
                    bucket[nd].push_back(w);
                }
            }
        }
    }

    // Output parent array
    for (int i = 0; i < N; ++i) {
        cout << parent[i] << (i == N-1 ? '\n' : ' ');
    }

    return 0;
}