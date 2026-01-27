#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>

using namespace std;

// Global variables to efficiently access data in SA loop
int n;
vector<int> D_flat; // Flattened distance matrix D
vector<vector<int>> F; // Flow matrix F (needed for O(1) checks)
vector<vector<int>> F_out; // Adjacency list for outgoing flow
vector<vector<int>> F_in;  // Adjacency list for incoming flow
vector<int> p; // Permutation: p[i] = location of facility i

int main() {
    // Optimize standard I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    // Read Distance Matrix D
    // Flatten it for potentially better cache locality and easier indexing
    D_flat.resize(n * n);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cin >> D_flat[i * n + j];
        }
    }

    // Read Flow Matrix F and build adjacency lists
    // Adjacency lists allow us to iterate only relevant neighbors, speeding up delta calculation on sparse matrices
    F.resize(n, vector<int>(n));
    F_out.resize(n);
    F_in.resize(n);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int val;
            cin >> val;
            F[i][j] = val;
            if (val) {
                F_out[i].push_back(j);
                F_in[j].push_back(i);
            }
        }
    }

    // --- Greedy Initialization ---
    // Strategy: Map facilities with high total flow (degree) to locations with low total distance (degree).
    // This minimizes the probability of mapping a flow edge to a distance edge (since D is binary, we want to map 1s in F to 0s in D).
    
    vector<pair<int, int>> flow_degrees(n);
    vector<pair<int, int>> dist_degrees(n);

    for (int i = 0; i < n; ++i) {
        int deg = 0;
        // Calculate total degree (in + out) for each facility in F
        for (int j = 0; j < n; ++j) deg += F[i][j] + F[j][i];
        flow_degrees[i] = {deg, i};
    }
    for (int i = 0; i < n; ++i) {
        int deg = 0;
        // Calculate total degree (in + out) for each location in D
        for (int j = 0; j < n; ++j) deg += D_flat[i * n + j] + D_flat[j * n + i];
        dist_degrees[i] = {deg, i};
    }

    // Sort facilities descending by flow degree (most connected first)
    sort(flow_degrees.rbegin(), flow_degrees.rend());
    // Sort locations ascending by distance degree (least connected first)
    sort(dist_degrees.begin(), dist_degrees.end());

    p.resize(n);
    for (int i = 0; i < n; ++i) {
        p[flow_degrees[i].second] = dist_degrees[i].second;
    }

    // --- Simulated Annealing ---
    auto start_time = chrono::high_resolution_clock::now();
    // Set a time limit slightly less than the typical 2s to ensure we output in time
    double time_limit = 1.9;

    mt19937 rng(1337);
    uniform_int_distribution<int> dist_n(0, n - 1);
    uniform_real_distribution<double> dist_01(0.0, 1.0);

    // Initial temperature and cooling factor
    double T = 0.5;
    double alpha = 0.999995;

    int iter = 0;
    while (true) {
        // Check time limit every 4096 iterations to reduce overhead
        if ((iter & 4095) == 0) {
            auto now = chrono::high_resolution_clock::now();
            chrono::duration<double> diff = now - start_time;
            if (diff.count() > time_limit) break;
        }
        iter++;

        // Select two distinct facilities to swap
        int i = dist_n(rng);
        int j = dist_n(rng);
        while (i == j) j = dist_n(rng);

        int u = p[i]; // current location of facility i
        int v = p[j]; // current location of facility j
        
        // Calculate change in cost (delta) if we swap locations of i and j
        int delta = 0;

        // Note: New location of i will be v, new location of j will be u.

        // 1. Edges outgoing from i (excluding j)
        for (int k : F_out[i]) {
            if (k == i || k == j) continue;
            int loc_k = p[k];
            // Old cost term: D[u][loc_k], New cost term: D[v][loc_k]
            delta += D_flat[v * n + loc_k] - D_flat[u * n + loc_k];
        }

        // 2. Edges incoming to i (excluding j)
        for (int k : F_in[i]) {
            if (k == i || k == j) continue;
            int loc_k = p[k];
            // Old: D[loc_k][u], New: D[loc_k][v]
            delta += D_flat[loc_k * n + v] - D_flat[loc_k * n + u];
        }

        // 3. Edges outgoing from j (excluding i)
        for (int k : F_out[j]) {
            if (k == i || k == j) continue;
            int loc_k = p[k];
            // Old: D[v][loc_k], New: D[u][loc_k]
            delta += D_flat[u * n + loc_k] - D_flat[v * n + loc_k];
        }

        // 4. Edges incoming to j (excluding i)
        for (int k : F_in[j]) {
            if (k == i || k == j) continue;
            int loc_k = p[k];
            // Old: D[loc_k][v], New: D[loc_k][u]
            delta += D_flat[loc_k * n + u] - D_flat[loc_k * n + v];
        }

        // 5. Interaction between i and j
        // Edge i -> j
        if (F[i][j]) {
            // Old: i at u, j at v -> D[u][v]
            // New: i at v, j at u -> D[v][u]
            delta += D_flat[v * n + u] - D_flat[u * n + v];
        }
        // Edge j -> i
        if (F[j][i]) {
            // Old: j at v, i at u -> D[v][u]
            // New: j at u, i at v -> D[u][v]
            delta += D_flat[u * n + v] - D_flat[v * n + u];
        }

        // 6. Self loops (i->i and j->j)
        if (F[i][i]) {
            delta += D_flat[v * n + v] - D_flat[u * n + u];
        }
        if (F[j][j]) {
            delta += D_flat[u * n + u] - D_flat[v * n + v];
        }

        // Metropolis acceptance criterion
        bool accept = false;
        if (delta <= 0) {
            accept = true;
        } else {
            if (dist_01(rng) < exp(-delta / T)) {
                accept = true;
            }
        }

        if (accept) {
            swap(p[i], p[j]);
        }

        // Cool down
        T *= alpha;
        if (T < 1e-7) T = 1e-7;
    }

    // Output result
    for (int i = 0; i < n; ++i) {
        cout << p[i] + 1 << (i == n - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}