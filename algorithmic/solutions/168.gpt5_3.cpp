#include <bits/stdc++.h>
using namespace std;

struct BFSResult {
    vector<int> dist;
    vector<int> parent;
    long long weightedSum;
    int maxDist;
};

static const int INF = 1e9;

static BFSResult multi_source_bfs(const vector<vector<int>>& adj, const vector<int>& roots_in, const vector<int>& A) {
    int N = adj.size();
    vector<int> roots = roots_in;
    vector<int> dist(N, INF);
    vector<int> parent(N, -1);
    queue<int> q;

    // Deduplicate roots
    sort(roots.begin(), roots.end());
    roots.erase(unique(roots.begin(), roots.end()), roots.end());

    for (int r : roots) {
        if (dist[r] > 0) {
            dist[r] = 0;
            parent[r] = -1;
            q.push(r);
        }
    }

    while (!q.empty()) {
        int u = q.front(); q.pop();
        int du = dist[u];
        for (int v : adj[u]) {
            if (dist[v] > du + 1) {
                dist[v] = du + 1;
                parent[v] = u;
                q.push(v);
            }
        }
    }

    long long S = 0;
    int dmax = 0;
    for (int i = 0; i < N; i++) {
        if (dist[i] >= INF/2) {
            // Should not happen in connected graph with at least one root, but guard
            dist[i] = INF/4;
        } else {
            S += 1LL * A[i] * dist[i];
            if (dist[i] > dmax) dmax = dist[i];
        }
    }

    return BFSResult{move(dist), move(parent), S, dmax};
}

static vector<int> gather_candidates_within_radius(const vector<vector<int>>& adj, int start, int L, const vector<int>& A, const vector<int>& current_roots, int K) {
    int N = adj.size();
    vector<int> depth(N, -1);
    queue<int> q;
    vector<int> nodes;
    depth[start] = 0;
    q.push(start);
    vector<char> is_root(N, 0);
    for (int r : current_roots) if (r >= 0 && r < N) is_root[r] = 1;

    while (!q.empty()) {
        int u = q.front(); q.pop();
        if (u != start) nodes.push_back(u);
        if (depth[u] == L) continue;
        for (int v : adj[u]) {
            if (depth[v] == -1) {
                depth[v] = depth[u] + 1;
                q.push(v);
            }
        }
    }

    // Sort by smaller A first, then by depth (prefer closer), then by index
    stable_sort(nodes.begin(), nodes.end(), [&](int x, int y){
        if (A[x] != A[y]) return A[x] < A[y];
        if (depth[x] != depth[y]) return depth[x] < depth[y];
        return x < y;
    });

    vector<int> cand;
    cand.reserve(min(K, (int)nodes.size()));
    for (int v : nodes) {
        if ((int)cand.size() >= K) break;
        if (is_root[v]) continue; // avoid colliding with other roots
        cand.push_back(v);
    }
    return cand;
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

    vector<vector<int>> adj(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    // Read coordinates, unused
    for (int i = 0; i < N; i++) {
        int x, y;
        cin >> x >> y;
    }

    // Initial roots: farthest-first, choose minimal A among farthest when need to add
    vector<int> roots;
    // Start with the vertex with minimal A
    int r0 = min_element(A.begin(), A.end()) - A.begin();
    roots.push_back(r0);

    while (true) {
        BFSResult res = multi_source_bfs(adj, roots, A);
        if (res.maxDist <= H) break;
        int dmax = res.maxDist;
        int best = -1;
        int bestA = INT_MAX;
        for (int i = 0; i < N; i++) {
            if (res.dist[i] == dmax) {
                if (A[i] < bestA || (A[i] == bestA && i < best)) {
                    bestA = A[i];
                    best = i;
                }
            }
        }
        if (best == -1) break; // should not happen
        roots.push_back(best);
    }

    // Remove redundant roots if possible
    {
        bool changed = true;
        while (changed) {
            changed = false;
            // Ensure unique roots
            sort(roots.begin(), roots.end());
            roots.erase(unique(roots.begin(), roots.end()), roots.end());
            for (int i = 0; i < (int)roots.size(); i++) {
                vector<int> tmp = roots;
                tmp.erase(tmp.begin() + i);
                BFSResult res = multi_source_bfs(adj, tmp, A);
                if (res.maxDist <= H) {
                    roots = move(tmp);
                    changed = true;
                    break;
                }
            }
        }
    }

    // Local improvement: move roots to nearby lower-A vertices if it increases weighted sum while keeping maxDist <= H
    {
        BFSResult base = multi_source_bfs(adj, roots, A);
        long long S = base.weightedSum;

        // Order roots by decreasing A to move high-A roots first
        vector<int> order = roots;
        sort(order.begin(), order.end(), [&](int x, int y){
            if (A[x] != A[y]) return A[x] > A[y];
            return x < y;
        });

        for (int r : order) {
            // find position of r in roots
            int pos = -1;
            for (int i = 0; i < (int)roots.size(); i++) if (roots[i] == r) { pos = i; break; }
            if (pos == -1) continue;

            const int L = 3; // search radius
            const int K = 8; // number of candidate positions to try
            vector<int> cands = gather_candidates_within_radius(adj, r, L, A, roots, K);

            // Also allow staying if needed
            // Try candidates with A <= A[r] preferentially
            for (int cand : cands) {
                if (A[cand] > A[r]) continue; // prefer not to increase A at root
                vector<int> tmp = roots;
                tmp[pos] = cand;
                // dedup
                sort(tmp.begin(), tmp.end());
                tmp.erase(unique(tmp.begin(), tmp.end()), tmp.end());
                BFSResult res = multi_source_bfs(adj, tmp, A);
                if (res.maxDist <= H && res.weightedSum >= S) {
                    // accept if improves or equal
                    if (res.weightedSum > S || (res.weightedSum == S && A[cand] < A[r])) {
                        roots = move(tmp);
                        S = res.weightedSum;
                        break;
                    }
                }
            }
        }

        // One more pass of removal after moves
        bool changed = true;
        while (changed) {
            changed = false;
            sort(roots.begin(), roots.end());
            roots.erase(unique(roots.begin(), roots.end()), roots.end());
            for (int i = 0; i < (int)roots.size(); i++) {
                vector<int> tmp = roots;
                tmp.erase(tmp.begin() + i);
                BFSResult res = multi_source_bfs(adj, tmp, A);
                if (res.maxDist <= H) {
                    roots = move(tmp);
                    changed = true;
                    break;
                }
            }
        }
    }

    // Final BFS to get parent assignment
    BFSResult final_res = multi_source_bfs(adj, roots, A);
    vector<int> parent = move(final_res.parent);

    // Output
    for (int i = 0; i < N; i++) {
        if (i) cout << ' ';
        cout << parent[i];
    }
    cout << '\n';

    return 0;
}