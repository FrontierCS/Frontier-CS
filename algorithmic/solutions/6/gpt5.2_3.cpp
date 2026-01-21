#include <bits/stdc++.h>
using namespace std;

static vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    vector<vector<int>> g(N + 1);
    vector<vector<char>> adj(N + 1, vector<char>(N + 1, 0));
    for (int i = 0; i < M; i++) {
        int u = A[i], v = B[i];
        g[u].push_back(v);
        g[v].push_back(u);
        adj[u][v] = adj[v][u] = 1;
    }

    if (N == 1) {
        int K = 3;
        return vector<vector<int>>(K, vector<int>(K, 1));
    }

    // Build a spanning tree with BFS.
    vector<int> parent(N + 1, 0);
    vector<int> order;
    order.reserve(N);
    queue<int> q;
    parent[1] = -1;
    q.push(1);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        order.push_back(u);
        for (int v : g[u]) {
            if (parent[v] == 0) {
                parent[v] = u;
                q.push(v);
            }
        }
    }

    // Problem guarantees a valid map exists; for N>1 this implies connectivity.
    // If not connected, still attempt a fallback by connecting components via any existing edge path (best effort).
    if ((int)order.size() != N) {
        // Best-effort: connect remaining nodes arbitrarily to 1 (may violate constraints if truly disconnected).
        for (int v = 1; v <= N; v++) if (parent[v] == 0) parent[v] = 1;
    }

    vector<vector<int>> tree(N + 1);
    for (int v = 2; v <= N; v++) {
        int p = parent[v];
        if (p > 0) {
            tree[p].push_back(v);
            tree[v].push_back(p);
        }
    }

    // Euler tour on the tree (vertex sequence), consecutive vertices are tree-adjacent.
    vector<int> seq;
    seq.reserve(2 * N);
    function<void(int,int)> dfs = [&](int u, int p) {
        seq.push_back(u);
        for (int v : tree[u]) {
            if (v == p) continue;
            dfs(v, u);
            seq.push_back(u);
        }
    };
    dfs(1, 0);

    int L = (int)seq.size();
    const int W = 3;
    int K = W * L;
    if (K > 240) {
        // Shouldn't happen with N<=40 and this construction (K<=237). Fallback compress width.
        // Reduce W to 2 (still gives an interior column only if W>=3, so keep safe by capping K and stretching rows).
        // But constraints imply this won't be needed.
        K = 240;
    }

    vector<vector<int>> C(K, vector<int>(K, 1));
    for (int t = 0; t < L; t++) {
        int color = seq[t];
        for (int col = W * t; col < W * t + W && col < K; col++) {
            for (int row = 0; row < K; row++) C[row][col] = color;
        }
    }

    vector<vector<char>> realized(N + 1, vector<char>(N + 1, 0));
    for (int t = 0; t + 1 < L; t++) {
        int a = seq[t], b = seq[t + 1];
        int u = min(a, b), v = max(a, b);
        realized[u][v] = 1;
    }

    vector<vector<int>> stripes(N + 1);
    stripes.assign(N + 1, {});
    for (int t = 0; t < L; t++) stripes[seq[t]].push_back(t);

    vector<int> nextStripeIdx(N + 1, 0);
    vector<int> rowPtr(L, 1);
    vector<vector<char>> usedRow(L, vector<char>(K, 0)); // usedRow[stripe][row]

    auto find_row = [&](int stripe) -> int {
        int start = rowPtr[stripe];
        auto ok = [&](int r) -> bool {
            if (r < 1 || r > K - 2) return false;
            if (usedRow[stripe][r]) return false;
            if (usedRow[stripe][r - 1]) return false;
            if (usedRow[stripe][r + 1]) return false;
            return true;
        };

        for (int pass = 0; pass < 2; pass++) {
            for (int r = start; r <= K - 2; r += 2) {
                if (ok(r)) {
                    rowPtr[stripe] = r + 2;
                    return r;
                }
            }
            start = 1;
        }
        for (int r = 1; r <= K - 2; r++) {
            if (ok(r)) {
                rowPtr[stripe] = r + 1;
                return r;
            }
        }
        return 1; // should never happen
    };

    for (int i = 0; i < M; i++) {
        int u = A[i], v = B[i];
        if (realized[u][v]) continue;

        // Place a single cell of v inside an interior column of a stripe of u.
        if (stripes[u].empty()) continue; // should not happen
        int idx = nextStripeIdx[u]++ % (int)stripes[u].size();
        int t = stripes[u][idx];
        int col = W * t + 1;
        if (col <= 0 || col >= K - 1) col = min(max(W * t, 0), K - 1); // best-effort fallback
        int r = find_row(t);

        C[r][col] = v;
        usedRow[t][r] = 1;
        realized[u][v] = 1;
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
            cout << K;
        }
        cout << "\n";
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