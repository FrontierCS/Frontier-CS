#include <bits/stdc++.h>
using namespace std;

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    // Build adjacency list
    vector<vector<int>> g(N + 1);
    vector<vector<bool>> adj(N + 1, vector<bool>(N + 1, false));
    for (int i = 0; i < M; ++i) {
        int u = A[i], v = B[i];
        g[u].push_back(v);
        g[v].push_back(u);
        adj[u][v] = adj[v][u] = true;
    }
    // Handle N=1 separately
    if (N == 1) {
        // Any K >=1, choose K=1
        return vector<vector<int>>(1, vector<int>(1, 1));
    }
    // Build a spanning tree using DFS
    vector<vector<int>> treeAdj(N + 1);
    vector<int> vis(N + 1, 0);
    vector<pair<int,int>> treeEdges;
    function<void(int)> dfs_build = [&](int u){
        vis[u] = 1;
        for (int v : g[u]) {
            if (!vis[v]) {
                treeAdj[u].push_back(v);
                treeAdj[v].push_back(u);
                treeEdges.emplace_back(u, v);
                dfs_build(v);
            }
        }
    };
    // Assume graph is connected as per problem guarantee
    dfs_build(1);

    // Mark tree edges
    vector<vector<bool>> isTree(N + 1, vector<bool>(N + 1, false));
    for (auto &e : treeEdges) {
        int u = e.first, v = e.second;
        isTree[u][v] = isTree[v][u] = true;
    }

    // Generate Euler tour-like sequence on the tree: seq length = 2N - 1
    vector<int> seq;
    function<void(int,int)> euler = [&](int u, int p){
        seq.push_back(u);
        for (int v : treeAdj[u]) {
            if (v == p) continue;
            euler(v, u);
            seq.push_back(u);
        }
    };
    euler(1, 0);

    int L = (int)seq.size();

    // First occurrence index for each vertex in seq
    vector<int> firstOcc(N + 1, -1);
    for (int i = 0; i < L; ++i) {
        int u = seq[i];
        if (firstOcc[u] == -1) firstOcc[u] = i;
    }

    // Assign non-tree edges to one endpoint (the one with earlier first occurrence)
    vector<vector<int>> islands(N + 1);
    for (int i = 0; i < M; ++i) {
        int u = A[i], v = B[i];
        if (isTree[u][v]) continue; // tree edge will be realized by band boundaries
        int assign = (firstOcc[u] <= firstOcc[v]) ? u : v;
        int other = (assign == u ? v : u);
        islands[assign].push_back(other);
    }

    // Compute required width per vertex band
    auto bandWidth = [&](int u)->int{
        // Only place islands on the first occurrence band
        // Each island uses pattern: ... u v u ... so width = 1 + 2 * (#islands[u])
        return 1 + 2 * (int)islands[u].size();
    };

    int W_base = 1;
    for (int u = 1; u <= N; ++u) {
        W_base = max(W_base, bandWidth(u));
    }

    int H = 3 * L;
    int K = max(H, W_base);
    if (K < 1) K = 1;
    K = min(K, 240); // Safety, though our construction ensures K <= 237.

    vector<vector<int>> C(K, vector<int>(K, 1));

    // Build the grid
    for (int r = 0; r < K; ++r) {
        int bandIdx, kind;
        int u;
        if (r < H) {
            bandIdx = r / 3;
            kind = r % 3; // 0: top u, 1: middle (with islands), 2: bottom u
            u = seq[bandIdx];
        } else {
            // Fill remaining rows with last band's bottom row to avoid new adjacencies
            bandIdx = L - 1;
            kind = 2;
            u = seq[bandIdx];
        }

        if (kind != 1) {
            // Uniform row of color u
            for (int c = 0; c < K; ++c) C[r][c] = u;
        } else {
            // Middle row: only place islands if this is the first occurrence band for u
            if (bandIdx == firstOcc[u]) {
                int pos = 0;
                if (pos < K) C[r][pos++] = u;
                for (int v : islands[u]) {
                    if (pos < K) C[r][pos++] = v;
                    if (pos < K) C[r][pos++] = u;
                }
                // Fill the rest with u
                for (; pos < K; ++pos) C[r][pos] = u;
            } else {
                // Not first occurrence band: keep uniform u
                for (int c = 0; c < K; ++c) C[r][c] = u;
            }
        }
    }

    return C;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int N, M;
        cin >> N >> M;
        vector<int> A(M), B(M);
        for (int i = 0; i < M; ++i) cin >> A[i] >> B[i];
        vector<vector<int>> C = create_map(N, M, A, B);
        int P = (int)C.size();
        cout << P << "\n";
        for (int i = 0; i < P; ++i) {
            cout << (int)C[i].size() << (i + 1 == P ? '\n' : ' ');
        }
        cout << "\n";
        for (int i = 0; i < P; ++i) {
            for (int j = 0; j < (int)C[i].size(); ++j) {
                cout << C[i][j] << (j + 1 == (int)C[i].size() ? '\n' : ' ');
            }
        }
        cout.flush();
    }
    return 0;
}