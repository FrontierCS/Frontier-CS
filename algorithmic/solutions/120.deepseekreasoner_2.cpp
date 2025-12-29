#include <bits/stdc++.h>
using namespace std;

int query(int a, int b, int c) {
    cout << "? " << a << ' ' << b << ' ' << c << endl;
    cout.flush();
    int ans;
    cin >> ans;
    return ans;
}

int main() {
    const int N = 100;
    vector<vector<int>> adj(N, vector<int>(N, 0));

    // Process 20 groups of 5 vertices each
    for (int g = 0; g < 20; ++g) {
        vector<int> group;
        for (int j = 1; j <= 5; ++j) {
            int v = g * 5 + j;
            group.push_back(v);
        }

        // Determine internal edges of the group by brute force
        vector<pair<int, int>> pairs;
        for (int i = 0; i < 5; ++i)
            for (int j = i + 1; j < 5; ++j)
                pairs.emplace_back(i, j);

        int m = pairs.size(); // m = 10
        vector<tuple<int, int, int>> triples;
        for (int i = 0; i < 5; ++i)
            for (int j = i + 1; j < 5; ++j)
                for (int k = j + 1; k < 5; ++k)
                    triples.emplace_back(i, j, k);

        vector<int> triple_res;
        for (auto [i, j, k] : triples) {
            int a = group[i], b = group[j], c = group[k];
            triple_res.push_back(query(a, b, c));
        }

        vector<int> best_edges(m, 0);
        for (int mask = 0; mask < (1 << m); ++mask) {
            vector<int> edges(m);
            for (int e = 0; e < m; ++e)
                edges[e] = (mask >> e) & 1;

            bool ok = true;
            for (size_t t = 0; t < triples.size(); ++t) {
                auto [i, j, k] = triples[t];
                int e_ij = -1, e_ik = -1, e_jk = -1;
                for (int e = 0; e < m; ++e) {
                    auto [u, v] = pairs[e];
                    if ((u == i && v == j) || (u == j && v == i)) e_ij = edges[e];
                    if ((u == i && v == k) || (u == k && v == i)) e_ik = edges[e];
                    if ((u == j && v == k) || (u == k && v == j)) e_jk = edges[e];
                }
                if (e_ij + e_ik + e_jk != triple_res[t]) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                best_edges = edges;
                break;
            }
        }

        for (int e = 0; e < m; ++e) {
            auto [i, j] = pairs[e];
            int u = group[i], v = group[j];
            adj[u - 1][v - 1] = adj[v - 1][u - 1] = best_edges[e];
        }

        // Connect all later vertices to this group
        int start_v = group.back() + 1;
        for (int v = start_v; v <= N; ++v) {
            vector<int> d(5);
            for (int i = 0; i < 5; ++i) {
                int gi = group[i];
                int gj = group[(i + 1) % 5];
                int res = query(v, gi, gj);
                int e_ij = adj[gi - 1][gj - 1];
                d[i] = res - e_ij;
            }
            int s = d[0] + d[2] + d[4] - d[1] - d[3];
            int x0 = s / 2;
            vector<int> x(5);
            x[0] = x0;
            for (int i = 1; i < 5; ++i)
                x[i] = d[i - 1] - x[i - 1];
            for (int i = 0; i < 5; ++i) {
                int gi = group[i];
                adj[v - 1][gi - 1] = adj[gi - 1][v - 1] = x[i];
            }
        }
    }

    cout << "!" << endl;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j)
            cout << adj[i][j];
        cout << endl;
    }
    cout.flush();
    return 0;
}