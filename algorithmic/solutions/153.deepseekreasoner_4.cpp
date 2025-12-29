#include <iostream>
#include <vector>
#include <unordered_map>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <utility>

using namespace std;

const int N = 400;
const int M = 1995;

struct Edge {
    int u, v, d;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> x(N), y(N);
    for (int i = 0; i < N; ++i) {
        cin >> x[i] >> y[i];
    }

    vector<Edge> edges(M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        double dx = x[u] - x[v];
        double dy = y[u] - y[v];
        int d = (int)round(sqrt(dx*dx + dy*dy));
        edges[i] = {u, v, d};
    }

    // DSU
    vector<int> parent(N);
    vector<int> sz(N, 1);
    iota(parent.begin(), parent.end(), 0);

    auto find = [&](int a) {
        while (parent[a] != a) {
            parent[a] = parent[parent[a]];
            a = parent[a];
        }
        return a;
    };

    // pending edge counts between components (only for roots)
    vector<unordered_map<int, int>> cnt(N);

    // Initialize with all edges
    for (const auto& e : edges) {
        int u = e.u, v = e.v;
        cnt[u][v]++;
        cnt[v][u]++;
    }

    for (int i = 0; i < M; ++i) {
        int l;
        cin >> l;
        int u = edges[i].u, v = edges[i].v, d = edges[i].d;
        int a = find(u);
        int b = find(v);
        int output = 0;

        if (a == b) {
            // Already connected, reject
            output = 0;
        } else {
            int num = cnt[a][b];  // number of pending edges between a and b (including current)
            if (num == 1) {
                // Last chance to connect these components
                output = 1;
            } else {
                // Adopt if the length is not worse than twice the Euclidean distance
                if (l <= 2 * d) {
                    output = 1;
                } else {
                    output = 0;
                }
            }

            // Update data structures
            if (output == 1) {
                // Remove current edge
                cnt[a][b]--;
                if (cnt[a][b] == 0) cnt[a].erase(b);
                cnt[b][a]--;
                if (cnt[b][a] == 0) cnt[b].erase(a);

                // Remove all other pending edges between a and b (they become internal)
                cnt[a].erase(b);
                cnt[b].erase(a);

                // Union by size
                if (sz[a] < sz[b]) swap(a, b);
                parent[b] = a;
                sz[a] += sz[b];

                // Merge pending lists of b into a
                vector<pair<int, int>> b_entries(cnt[b].begin(), cnt[b].end());
                for (auto [c, count] : b_entries) {
                    if (c == a) continue;
                    cnt[a][c] += count;
                    cnt[c][a] += count;
                    cnt[c].erase(b);
                }
                cnt[b].clear();
            } else {
                // Reject: just remove this edge
                cnt[a][b]--;
                if (cnt[a][b] == 0) cnt[a].erase(b);
                cnt[b][a]--;
                if (cnt[b][a] == 0) cnt[b].erase(a);
            }
        }

        cout << output << endl;
        cout.flush();
    }

    return 0;
}