#include <bits/stdc++.h>
using namespace std;

static constexpr int N = 100;

int query(int a, int b, int c) {
    cout << "? " << a << " " << b << " " << c << "\n";
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (r < 0) exit(0);
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<vector<int>> adj(N + 1, vector<int>(N + 1, 0));

    // Bootstrap with first K vertices: query all triples and brute force all edges.
    const int K = 6;
    vector<array<int, 3>> triples;
    triples.reserve(K * (K - 1) * (K - 2) / 6);
    for (int a = 1; a <= K; ++a)
        for (int b = a + 1; b <= K; ++b)
            for (int c = b + 1; c <= K; ++c)
                triples.push_back({a, b, c});

    vector<int> tripleAns(triples.size());
    for (size_t i = 0; i < triples.size(); ++i) {
        auto [a, b, c] = triples[i];
        tripleAns[i] = query(a, b, c);
    }

    vector<pair<int,int>> edges;
    edges.reserve(K * (K - 1) / 2);
    vector<vector<int>> eidx(K + 1, vector<int>(K + 1, -1));
    for (int i = 1; i <= K; ++i) {
        for (int j = i + 1; j <= K; ++j) {
            int id = (int)edges.size();
            edges.push_back({i, j});
            eidx[i][j] = eidx[j][i] = id;
        }
    }
    int E = (int)edges.size(); // 15

    vector<array<int,3>> tripleEdgeIdx(triples.size());
    for (size_t ti = 0; ti < triples.size(); ++ti) {
        auto [a, b, c] = triples[ti];
        tripleEdgeIdx[ti] = { eidx[a][b], eidx[a][c], eidx[b][c] };
    }

    int solMask = -1;
    for (int mask = 0; mask < (1 << E); ++mask) {
        bool ok = true;
        for (size_t ti = 0; ti < triples.size(); ++ti) {
            auto [i1, i2, i3] = tripleEdgeIdx[ti];
            int cnt = ((mask >> i1) & 1) + ((mask >> i2) & 1) + ((mask >> i3) & 1);
            if (cnt != tripleAns[ti]) { ok = false; break; }
        }
        if (ok) { solMask = mask; break; }
    }
    if (solMask < 0) exit(0);

    for (int id = 0; id < E; ++id) {
        auto [u, v] = edges[id];
        int val = (solMask >> id) & 1;
        adj[u][v] = adj[v][u] = val;
    }

    // Add remaining vertices one by one.
    for (int v = K + 1; v <= N; ++v) {
        int t = v - 1;
        vector<int> sum(t); // sum[i] for i=1..t-1 stores x_i + x_{i+1}
        for (int i = 1; i <= t - 1; ++i) {
            int r = query(i, i + 1, v);
            int s = r - adj[i][i + 1];
            if (s < 0 || s > 2) exit(0);
            sum[i] = s;
        }

        vector<int> x(t + 1, -1);
        int anchor = -1;
        for (int i = 1; i <= t - 1; ++i) {
            if (sum[i] != 1) { anchor = i; break; }
        }

        if (anchor != -1) {
            int val = sum[anchor] / 2; // 0 or 1
            x[anchor] = x[anchor + 1] = val;

            for (int i = anchor - 1; i >= 1; --i) {
                int xi = sum[i] - x[i + 1];
                if (xi < 0 || xi > 1) exit(0);
                x[i] = xi;
            }
            for (int i = anchor + 1; i <= t - 1; ++i) {
                int xi1 = sum[i] - x[i];
                if (xi1 < 0 || xi1 > 1) exit(0);
                x[i + 1] = xi1;
            }
        } else {
            // all sums are 1 => alternating, need one extra query to fix absolute
            int r = query(1, 3, v);
            int s = r - adj[1][3];
            if (s != 0 && s != 2) exit(0);
            int x1 = s / 2;
            for (int i = 1; i <= t; ++i) x[i] = x1 ^ ((i - 1) & 1);
        }

        for (int i = 1; i <= t; ++i) {
            adj[v][i] = adj[i][v] = x[i];
        }
    }

    cout << "!\n";
    for (int i = 1; i <= N; ++i) {
        string s;
        s.reserve(N);
        for (int j = 1; j <= N; ++j) {
            s.push_back((i != j && adj[i][j]) ? '1' : '0');
        }
        cout << s << "\n";
    }
    cout.flush();
    return 0;
}