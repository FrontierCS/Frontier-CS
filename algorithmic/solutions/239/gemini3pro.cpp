#include <iostream>
#include <vector>

using namespace std;

// Global variables to store graph and results
int n;
// Adjacency matrix to keep track of existing edges.
// N <= 4096, so 4100x4100 bool array takes ~16MB, well within 512MB limit.
bool adj[4100][4100];

struct Edge {
    int u, c, v;
};
vector<Edge> result;

// Helper to add an edge if it doesn't strictly exist
void add_edge(int u, int c, int v) {
    if (adj[u][v]) return;
    // Condition: can add u->v only if u->c and c->v exist
    if (adj[u][c] && adj[c][v]) {
        adj[u][v] = true;
        result.push_back({u, c, v});
    }
}

// Recursively builds edges i -> R for all i in [L, R)
// This ensures that the right endpoint of the interval is reachable from all nodes within it in 1 step.
void solve_right(int L, int R) {
    if (L >= R) return;
    if (R - L == 1) return; // Base edge i -> i+1 already exists

    int M = (L + R) / 2;
    solve_right(L, M);
    solve_right(M, R);
    
    // After recursion:
    // For i in [L, M), edge i -> M exists.
    // For j in [M, R), edge j -> R exists.
    // Specifically, M -> R exists because M is the start of [M, R).
    
    // We can now add i -> R for all i in [L, M) using the path i -> M -> R
    for (int i = L; i < M; ++i) {
        add_edge(i, M, R);
    }
}

// Recursively builds edges L -> j for all j in (L, R]
// This ensures that the left endpoint of the interval can reach all nodes within it in 1 step.
void solve_left(int L, int R) {
    if (L >= R) return;
    if (R - L == 1) return;

    int M = (L + R) / 2;
    solve_left(L, M);
    solve_left(M, R);
    
    // After recursion:
    // For i in (L, M], edge L -> i exists.
    // For j in (M, R], edge M -> j exists.
    // Specifically, L -> M exists.
    
    // We can now add L -> j for all j in (M, R] using the path L -> M -> j
    for (int j = M + 1; j <= R; ++j) {
        add_edge(L, M, j);
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    // Initialize adjacency matrix
    for (int i = 0; i <= n; ++i) {
        for (int j = 0; j <= n; ++j) {
            adj[i][j] = false;
        }
    }
    // Initial edges: v -> v + 1
    for (int i = 0; i < n; ++i) {
        adj[i][i+1] = true;
    }

    // Solve for both directions to ensure coverage
    // This construction guarantees that for any u < v, there is a common interval [A, B]
    // with midpoint M such that u is in [A, M) and v is in [M, B].
    // solve_right ensures u -> M exists.
    // solve_left ensures M -> v exists.
    // Thus u -> M -> v is a path of length 2.
    solve_right(0, n);
    solve_left(0, n);

    cout << result.size() << "\n";
    for (const auto& e : result) {
        cout << e.u << " " << e.c << " " << e.v << "\n";
    }

    return 0;
}