#include <iostream>
#include <vector>
#include <numeric>

void solve() {
    int n, m;
    std::cin >> n >> m;

    std::vector<std::vector<int>> adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            std::cout << 0 << (i == n - 1 ? "" : " ");
        }
        std::cout << std::endl;
        return;
    }

    std::vector<int> partition(n + 1, -1);

    // Phase 1: Greedy construction.
    // Assign vertices sequentially to the partition that maximizes
    // cuts with already-assigned neighbors.
    for (int i = 1; i <= n; ++i) {
        int count0 = 0;
        int count1 = 0;
        for (int neighbor : adj[i]) {
            if (partition[neighbor] == 0) {
                count0++;
            } else if (partition[neighbor] == 1) {
                count1++;
            }
        }
        // To maximize new cuts, place in set 1 if it has more neighbors in set 0,
        // and vice versa.
        if (count0 > count1) {
            partition[i] = 1;
        } else {
            partition[i] = 0;
        }
    }

    // Phase 2: Local search (iterative improvement).
    // Repeatedly scan vertices and flip their partition if it improves the cut,
    // until a local optimum is reached.
    bool changed = true;
    while (changed) {
        changed = false;
        for (int i = 1; i <= n; ++i) {
            int count_same = 0;
            int count_other = 0;
            for (int neighbor : adj[i]) {
                if (partition[neighbor] == partition[i]) {
                    count_same++;
                } else {
                    count_other++;
                }
            }
            // If a vertex has more neighbors in its own set, moving it
            // to the other set will increase the cut size.
            if (count_same > count_other) {
                partition[i] = 1 - partition[i]; // Flip partition
                changed = true;
            }
        }
    }

    // Output the resulting partition.
    for (int i = 1; i <= n; ++i) {
        std::cout << partition[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}