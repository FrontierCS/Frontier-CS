#include <bits/stdc++.h>
using namespace std;

int query(int a, int b, int c) {
    cout << "? " << a << ' ' << b << ' ' << c << endl;
    cout.flush();
    int t;
    if (!(cin >> t)) {
        exit(0);
    }
    if (t < 0) {
        exit(0);
    }
    return t;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int n = 100;
    const int BASE = 5;

    vector<vector<int>> adj(n + 1, vector<int>(n + 1, 0));

    // Base step: reconstruct induced subgraph on vertices 1..5 using all triples among them
    long long A[BASE + 1] = {0};
    long long S[BASE + 1][BASE + 1] = {0};
    long long T = 0;

    for (int i = 1; i <= BASE; ++i)
        for (int j = 1; j <= BASE; ++j)
            S[i][j] = 0;

    for (int i = 1; i <= BASE; ++i) {
        for (int j = i + 1; j <= BASE; ++j) {
            for (int k = j + 1; k <= BASE; ++k) {
                int t = query(i, j, k);
                T += t;
                A[i] += t;
                A[j] += t;
                A[k] += t;
                S[i][j] += t;
                S[i][k] += t;
                S[j][k] += t;
            }
        }
    }

    long long M = T / (BASE - 2); // total edges among first BASE vertices
    long long deg[BASE + 1];
    for (int i = 1; i <= BASE; ++i) {
        deg[i] = (A[i] - M) / (BASE - 3);
    }

    for (int i = 1; i <= BASE; ++i) {
        for (int j = i + 1; j <= BASE; ++j) {
            long long xij = (S[i][j] - deg[i] - deg[j]) / (BASE - 4);
            adj[i][j] = adj[j][i] = (int)xij;
        }
    }

    // Extension: add vertices BASE+1..n using anchors 1,2,3
    int a = 1, b = 2, c = 3;

    for (int v = BASE + 1; v <= n; ++v) {
        int t_abv = query(a, b, v);
        int t_acv = query(a, c, v);
        int t_bcv = query(b, c, v);

        int x_ab = adj[a][b];
        int x_ac = adj[a][c];
        int x_bc = adj[b][c];

        int s1 = t_abv - x_ab; // x_av + x_bv
        int s2 = t_acv - x_ac; // x_av + x_cv
        int s3 = t_bcv - x_bc; // x_bv + x_cv

        int x_av = (s1 + s2 - s3) / 2;
        int x_bv = s1 - x_av;
        int x_cv = s2 - x_av;

        adj[a][v] = adj[v][a] = x_av;
        
        adj[b][v] = adj[v][b] = x_bv;
        adj[c][v] = adj[v][c] = x_cv;

        for (int u = 1; u < v; ++u) {
            if (u == a || u == b || u == c) continue;
            int t_auv = query(a, u, v);
            int x_au = adj[a][u];
            int x_uv = t_auv - x_au - x_av;
            adj[u][v] = adj[v][u] = x_uv;
        }
    }

    // Output the reconstructed adjacency matrix
    cout << "!" << '\n';
    for (int i = 1; i <= n; ++i) {
        string row;
        row.reserve(n);
        for (int j = 1; j <= n; ++j) {
            if (i == j) row.push_back('0');
            else row.push_back(adj[i][j] ? '1' : '0');
        }
        cout << row << '\n';
    }
    cout.flush();

    return 0;
}