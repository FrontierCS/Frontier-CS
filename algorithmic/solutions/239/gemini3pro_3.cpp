#include <iostream>
#include <vector>
#include <bitset>

using namespace std;

// Maximum N is 2^12 = 4096. We need indices up to N.
const int MAXN = 4105;

int N;
struct Edge {
    int u, c, v;
};
vector<Edge> added_edges;
bitset<MAXN> adj[MAXN];

// Function to add an edge if it doesn't exist
void add_edge(int u, int c, int v) {
    if (adj[u][v]) return;
    adj[u][v] = 1;
    added_edges.push_back({u, c, v});
}

// Recursive function to solve for range [L, R]
// Ensures that for any u in [L, M] and v in [M, R], dist(u, v) <= 2.
// Also ensures that for any u, v in [L, R], dist(u, v) <= 3.
void solve(int L, int R) {
    // Base case: if range size is small, max distance is already <= 3
    if (R - L <= 3) return;

    int M = (L + R) / 2;
    solve(L, M);
    solve(M, R);

    // To facilitate crossing M with distance <= 2 (u -> M -> v):
    // 1. Build edges u -> M for u in [L, M-1].
    //    We iterate backwards from M-2 to L.
    //    We rely on i -> i+1 (always exists) and i+1 -> M (built in previous step or base case M-1->M).
    for (int i = M - 2; i >= L; --i) {
        if (adj[i][i+1] && adj[i+1][M]) {
            add_edge(i, i+1, M);
        }
    }

    // 2. Build edges M -> v for v in [M+1, R].
    //    We iterate forwards from M+2 to R.
    //    We rely on M -> j-1 (built in previous step) and j-1 -> j (always exists).
    for (int j = M + 2; j <= R; ++j) {
        if (adj[M][j-1] && adj[j-1][j]) {
            add_edge(M, j-1, j);
        }
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;

    // Initialize graph with edges i -> i+1
    for (int i = 0; i < N; ++i) {
        adj[i][i+1] = 1;
    }

    solve(0, N);

    // Output results
    cout << added_edges.size() << "\n";
    for (const auto& e : added_edges) {
        cout << e.u << " " << e.c << " " << e.v << "\n";
    }

    return 0;
}