#include <bits/stdc++.h>
using namespace std;

int query(int a, int b, int c) {
    cout << "? " << a << " " << b << " " << c << endl;
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int n = 100;
    vector<vector<int>> adj(n + 1, vector<int>(n + 1, 0));

    int a = 1, b = 2, c = 3, d = 4;

    // Queries among anchors
    int s1 = query(a, b, c);
    int s2 = query(a, b, d);
    int s3 = query(a, c, d);
    int s4 = query(b, c, d);

    // Compute differences among anchor pairs
    int Delta1 = (s1 + s2 - s3 - s4) / 2; // A_ab - A_cd
    int Delta2 = (s1 + s3 - s2 - s4) / 2; // A_ac - A_bd
    int Delta3 = (s2 + s3 - s1 - s4) / 2; // A_ad - A_bc

    int P = (s1 + s2 + s3 + s4) / 2; // sum of all 6 anchor edges

    // Store t values for vertex 5 to compute anchor edges later
    int v0 = 5;
    int t_ab_v0 = 0, t_ac_v0 = 0, t_ad_v0 = 0, t_bc_v0 = 0, t_bd_v0 = 0, t_cd_v0 = 0;

    for (int v = 5; v <= n; ++v) {
        int t_ab = query(a, b, v);
        int t_ac = query(a, c, v);
        int t_ad = query(a, d, v);
        int t_bc = query(b, c, v);
        int t_bd = query(b, d, v);
        int t_cd = query(c, d, v);

        if (v == v0) {
            t_ab_v0 = t_ab;
            t_ac_v0 = t_ac;
            t_ad_v0 = t_ad;
            t_bc_v0 = t_bc;
            t_bd_v0 = t_bd;
            t_cd_v0 = t_cd;
        }

        int Aplus = t_ab + t_cd;
        int Bplus = t_ac + t_bd;
        int Cplus = t_ad + t_bc;
        int S = (Aplus + Bplus + Cplus - P) / 3;

        int k1 = (t_ab - t_cd) - Delta1; // (x+y - z - w)
        int k2 = (t_ac - t_bd) - Delta2; // (x+z - y - w)
        int k3 = (t_ad - t_bc) - Delta3; // (x+w - y - z)

        int dxy = (k2 + k3) / 2; // x - y
        int dxz = (k1 + k3) / 2; // x - z
        int dxw = (k1 + k2) / 2; // x - w

        int x = (S + dxy + dxz + dxw) / 4;
        int y = x - dxy;
        int z = x - dxz;
        int w = x - dxw;

        adj[a][v] = adj[v][a] = x;
        adj[b][v] = adj[v][b] = y;
        adj[c][v] = adj[v][c] = z;
        adj[d][v] = adj[v][d] = w;
    }

    // Compute anchor pair edges using v0
    int A_ab = t_ab_v0 - adj[a][v0] - adj[b][v0];
    int A_ac = t_ac_v0 - adj[a][v0] - adj[c][v0];
    int A_ad = t_ad_v0 - adj[a][v0] - adj[d][v0];
    int A_bc = t_bc_v0 - adj[b][v0] - adj[c][v0];
    int A_bd = t_bd_v0 - adj[b][v0] - adj[d][v0];
    int A_cd = t_cd_v0 - adj[c][v0] - adj[d][v0];

    adj[a][b] = adj[b][a] = A_ab;
    adj[a][c] = adj[c][a] = A_ac;
    adj[a][d] = adj[d][a] = A_ad;
    adj[b][c] = adj[c][b] = A_bc;
    adj[b][d] = adj[d][b] = A_bd;
    adj[c][d] = adj[d][c] = A_cd;

    // Determine edges among non-anchors using vertex a as the third vertex
    for (int u = 5; u <= n; ++u) {
        for (int v = u + 1; v <= n; ++v) {
            int t = query(a, u, v);
            int uv = t - adj[a][u] - adj[a][v];
            if (uv < 0) uv = 0;
            if (uv > 1) uv = 1;
            adj[u][v] = adj[v][u] = uv;
        }
    }

    // Output the reconstructed adjacency matrix
    cout << "!" << endl;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (i == j) cout << '0';
            else cout << (adj[i][j] ? '1' : '0');
        }
        cout << "\n";
    }
    cout.flush();

    return 0;
}