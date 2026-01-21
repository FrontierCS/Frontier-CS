#include <bits/stdc++.h>
using namespace std;

static vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    if (N == 1) return vector<vector<int>>(1, vector<int>(1, 1));

    vector<vector<int>> g(N + 1);
    vector<vector<char>> adj(N + 1, vector<char>(N + 1, 0));
    for (int i = 0; i < M; i++) {
        int u = A[i], v = B[i];
        g[u].push_back(v);
        g[v].push_back(u);
        adj[u][v] = adj[v][u] = 1;
    }

    auto bfs_dist = [&](int s) {
        const int INF = 1e9;
        vector<int> dist(N + 1, INF);
        queue<int> q;
        dist[s] = 0;
        q.push(s);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : g[u]) if (dist[v] == INF) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
        return dist;
    };

    int root = 1;
    {
        int bestEcc = INT_MAX;
        for (int s = 1; s <= N; s++) {
            auto dist = bfs_dist(s);
            int ecc = 0;
            for (int v = 1; v <= N; v++) ecc = max(ecc, dist[v]);
            if (ecc < bestEcc) {
                bestEcc = ecc;
                root = s;
            }
        }
    }

    vector<int> parent(N + 1, -1), depth(N + 1, 0);
    queue<int> q;
    parent[root] = 0;
    depth[root] = 0;
    q.push(root);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : g[u]) if (parent[v] == -1) {
            parent[v] = u;
            depth[v] = depth[u] + 1;
            q.push(v);
        }
    }

    // Build children lists (spanning tree)
    vector<vector<int>> children(N + 1);
    for (int v = 1; v <= N; v++) if (v != root) {
        if (parent[v] <= 0) {
            // Should not happen if a map exists and N>1, but keep safe.
            parent[v] = root;
            depth[v] = depth[root] + 1;
        }
        children[parent[v]].push_back(v);
    }

    int maxDepth = 0;
    for (int v = 1; v <= N; v++) maxDepth = max(maxDepth, depth[v]);

    // Assign patches for non-tree edges
    vector<vector<int>> patches(N + 1);
    for (int i = 0; i < M; i++) {
        int a = A[i], b = B[i];
        if (parent[a] == b || parent[b] == a) continue; // tree edge already realized
        int u = a, v = b;
        if (depth[u] > depth[v]) swap(u, v);
        else if (depth[u] == depth[v] && u > v) swap(u, v);
        patches[u].push_back(v);
    }

    auto compute_heights = [&](int K, vector<int>& height_out) -> bool {
        height_out.assign(N + 1, 0);

        vector<int> patchCols(N + 1, 1), patchHeight(N + 1, 0);
        for (int u = 1; u <= N; u++) {
            int wrect = K - 2 * depth[u];
            if (wrect < 1) return false;

            if ((!children[u].empty() || !patches[u].empty()) && wrect < 3) return false;
            if (!patches[u].empty() && wrect < 5) return false;

            int innerW = max(0, wrect - 2);
            int cols = 1;
            if (innerW >= 3) cols = max(1, innerW / 3);
            patchCols[u] = cols;

            int p = (int)patches[u].size();
            int rows = (p + cols - 1) / cols;
            patchHeight[u] = 3 * rows;
        }

        vector<int> order(N);
        iota(order.begin(), order.end(), 1);
        stable_sort(order.begin(), order.end(), [&](int x, int y) {
            if (depth[x] != depth[y]) return depth[x] > depth[y];
            return x < y;
        });

        for (int u : order) {
            long long childSum = 0;
            for (int ch : children[u]) childSum += height_out[ch];
            long long childSep = (children[u].empty() ? 0LL : (long long)children[u].size() - 1);
            long long sepBetween = (!patches[u].empty() && !children[u].empty()) ? 1LL : 0LL;
            long long content = (long long)patchHeight[u] + sepBetween + childSum + childSep;
            long long h = max(2LL, 2LL + content);
            if (h > 1000000) return false; // paranoia
            height_out[u] = (int)h;
        }

        if (height_out[root] > K) return false;
        return true;
    };

    auto feasible = [&](int K) -> bool {
        if (K < 1 || K > 240) return false;
        vector<int> h;
        if (!compute_heights(K, h)) return false;

        // Also ensure we can nest widths down to maxDepth for nodes with nontrivial content.
        for (int u = 1; u <= N; u++) {
            int wrect = K - 2 * depth[u];
            if (wrect < 1) return false;
            if ((!children[u].empty() || !patches[u].empty()) && wrect < 3) return false;
            if (!patches[u].empty() && wrect < 5) return false;
        }
        return true;
    };

    int lo = 1, hi = 240, bestK = 240;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (feasible(mid)) {
            bestK = mid;
            hi = mid - 1;
        } else {
            lo = mid + 1;
        }
    }

    int K = bestK;
    vector<int> height;
    bool ok = compute_heights(K, height);
    if (!ok) {
        K = 240;
        compute_heights(K, height);
    }

    // Sort children for deterministic layout
    for (int u = 1; u <= N; u++) sort(children[u].begin(), children[u].end());
    for (int u = 1; u <= N; u++) {
        // Keep patches deterministic
        sort(patches[u].begin(), patches[u].end());
    }

    vector<vector<int>> C(K, vector<int>(K, root));

    struct Rect { int top, left, bottom, right; };

    function<void(int, Rect)> layout = [&](int u, Rect r) {
        for (int i = r.top; i <= r.bottom; i++) {
            for (int j = r.left; j <= r.right; j++) C[i][j] = u;
        }

        int wrect = r.right - r.left + 1;
        int innerW = wrect - 2;

        int cols = 1;
        if (innerW >= 3) cols = max(1, innerW / 3);

        int p = (int)patches[u].size();
        int rows = (p + cols - 1) / cols;
        int pH = 3 * rows;

        int row = r.top + 1;
        int col0 = r.left + 1;

        // Place patches as 3x3 blocks with center = v, surrounded by u.
        for (int idx = 0; idx < p; idx++) {
            int br = idx / cols;
            int bc = idx % cols;
            int baseR = row + 3 * br;
            int baseC = col0 + 3 * bc;
            int centerR = baseR + 1;
            int centerC = baseC + 1;
            if (centerR >= r.top + 1 && centerR <= r.bottom - 1 &&
                centerC >= r.left + 1 && centerC <= r.right - 1) {
                C[centerR][centerC] = patches[u][idx];
            }
        }

        row += pH;
        if (p > 0 && !children[u].empty()) row += 1;

        for (int i = 0; i < (int)children[u].size(); i++) {
            int ch = children[u][i];
            int hch = height[ch];
            Rect cr{row, r.left + 1, row + hch - 1, r.right - 1};
            layout(ch, cr);
            row = cr.bottom + 1;
            if (i + 1 < (int)children[u].size()) row += 1; // separator row in color u
        }
    };

    layout(root, Rect{0, 0, K - 1, K - 1});

    auto validate = [&]() -> bool {
        vector<int> cnt(N + 1, 0);
        static bool seen[41][41];
        for (int i = 1; i <= N; i++) for (int j = 1; j <= N; j++) seen[i][j] = false;

        for (int i = 0; i < K; i++) {
            for (int j = 0; j < K; j++) {
                int c = C[i][j];
                if (c < 1 || c > N) return false;
                cnt[c]++;
                if (i + 1 < K) {
                    int d = C[i + 1][j];
                    if (c != d) {
                        if (!adj[c][d]) return false;
                        int x = min(c, d), y = max(c, d);
                        seen[x][y] = true;
                    }
                }
                if (j + 1 < K) {
                    int d = C[i][j + 1];
                    if (c != d) {
                        if (!adj[c][d]) return false;
                        int x = min(c, d), y = max(c, d);
                        seen[x][y] = true;
                    }
                }
            }
        }
        for (int c = 1; c <= N; c++) if (cnt[c] == 0) return false;
        for (int i = 0; i < M; i++) {
            int u = A[i], v = B[i];
            if (!seen[u][v]) return false;
        }
        return true;
    };

    if (!validate()) {
        // Fallback: use maximum K and re-layout (should not happen).
        K = 240;
        compute_heights(K, height);
        C.assign(K, vector<int>(K, root));
        layout(root, Rect{0, 0, K - 1, K - 1});
        // No further fallback.
    }

    return C;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    for (int tc = 0; tc < T; tc++) {
        int N, M;
        cin >> N >> M;
        vector<int> A(M), B(M);
        for (int i = 0; i < M; i++) cin >> A[i] >> B[i];

        auto C = create_map(N, M, A, B);
        int K = (int)C.size();

        cout << K << "\n";
        for (int i = 0; i < K; i++) {
            if (i) cout << ' ';
            cout << (int)C[i].size();
        }
        cout << "\n\n";
        for (int i = 0; i < K; i++) {
            for (int j = 0; j < K; j++) {
                if (j) cout << ' ';
                cout << C[i][j];
            }
            cout << "\n";
        }
        if (tc + 1 < T) cout << "\n";
    }
    return 0;
}