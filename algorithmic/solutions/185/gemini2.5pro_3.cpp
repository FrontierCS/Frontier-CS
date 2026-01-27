#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <bitset>

const int MAXN = 1001;

int N, M;
std::bitset<MAXN> adj[MAXN];
std::vector<int> degree;

void solve() {
    std::cin >> N >> M;
    degree.assign(N, 0);

    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        --u; --v;
        if (!adj[u][v]) {
            adj[u][v] = 1;
            adj[v][u] = 1;
            degree[u]++;
            degree[v]++;
        }
    }

    std::vector<int> p(N);
    std::iota(p.begin(), p.end(), 0);
    std::sort(p.begin(), p.end(), [&](int u, int v) {
        return degree[u] > degree[v];
    });

    std::vector<int> best_clique;

    for (int i = 0; i < N; ++i) {
        int v = p[i];
        if (degree[v] + 1 <= (int)best_clique.size()) {
            continue;
        }

        std::vector<int> current_clique;
        current_clique.push_back(v);
        std::bitset<MAXN> candidates = adj[v];

        for (int j = i + 1; j < N; ++j) {
            int u = p[j];
            if (candidates[u]) {
                current_clique.push_back(u);
                candidates &= adj[u];
            }
        }
        if (current_clique.size() > best_clique.size()) {
            best_clique = current_clique;
        }
    }

    std::vector<bool> in_clique(N, false);
    for (int node : best_clique) {
        in_clique[node] = true;
    }
    for (int i = 0; i < N; ++i) {
        std::cout << (in_clique[i] ? 1 : 0) << "\n";
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}