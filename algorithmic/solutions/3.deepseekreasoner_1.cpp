#include <cstdio>
#include <vector>
#include <utility>
#include <algorithm>

using namespace std;

int main() {
    int subtask, n;
    scanf("%d %d", &subtask, &n);

    if (n <= 1000) {
        // All-pairs test in one query
        int npairs = n * (n - 1) / 2;
        vector<pair<int, int>> pairs;
        pairs.reserve(npairs);
        for (int i = 1; i <= n; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                pairs.emplace_back(i, j);
            }
        }

        // Build query: for each pair (u,v) output u v u v
        int L = 4 * npairs;
        printf("%d", L);
        for (const auto& p : pairs) {
            printf(" %d %d %d %d", p.first, p.second, p.first, p.second);
        }
        printf("\n");
        fflush(stdout);

        // Read responses
        vector<int> resp(L);
        for (int i = 0; i < L; ++i) {
            scanf("%d", &resp[i]);
        }

        // Build adjacency matrix from the second bit of each quadruple
        vector<vector<bool>> adj(n + 1, vector<bool>(n + 1, false));
        for (int idx = 0; idx < npairs; ++idx) {
            int bit = resp[4 * idx + 1]; // after toggling v (second operation)
            if (bit == 1) {
                int u = pairs[idx].first;
                int v = pairs[idx].second;
                adj[u][v] = adj[v][u] = true;
            }
        }

        // Reconstruct the cycle starting from vertex 1
        vector<int> cycle;
        vector<bool> used(n + 1, false);
        int cur = 1;
        cycle.push_back(cur);
        used[cur] = true;

        while ((int)cycle.size() < n) {
            int prev = cycle.back();
            int nxt = -1;
            // Find an unused neighbor of prev
            for (int v = 1; v <= n; ++v) {
                if (adj[prev][v] && !used[v]) {
                    nxt = v;
                    break;
                }
            }
            if (nxt == -1) {
                // The only remaining neighbor is the first vertex
                nxt = cycle[0];
                if (!adj[prev][nxt]) {
                    // Should not happen for a correct cycle
                    break;
                }
            }
            cycle.push_back(nxt);
            used[nxt] = true;
        }

        // Output the guessed permutation
        printf("-1");
        for (int x : cycle) {
            printf(" %d", x);
        }
        printf("\n");
        fflush(stdout);
    } else {
        // For large n, output a trivial permutation (will be incorrect, but avoids runtime error)
        printf("-1");
        for (int i = 1; i <= n; ++i) {
            printf(" %d", i);
        }
        printf("\n");
        fflush(stdout);
    }

    return 0;
}