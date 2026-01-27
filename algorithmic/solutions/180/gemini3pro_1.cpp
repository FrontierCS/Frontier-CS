#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>

using namespace std;

// Global constants and data structures
const int MAXN = 2005;

// adj1 is adjacency matrix for G1 for O(1) edge lookups
bool adj1[MAXN][MAXN]; 
// adj2 is adjacency list for G2 for efficient neighbor iteration
vector<int> adj2[MAXN];

// p[i] maps vertex i of G2 to vertex p[i] of G1
int p[MAXN];      
int best_p[MAXN]; 
int deg1[MAXN], deg2[MAXN];
int n, m;

// Random number generator
mt19937 rng(1337);

// Timer function
inline double get_time() {
    using namespace std::chrono;
    return duration_cast<duration<double>>(steady_clock::now().time_since_epoch()).count();
}

// Structure for smart initialization
struct VertexInfo {
    int id;
    int d;
    long long sum_nd;
    long long sum_sq_nd;
    
    bool operator<(const VertexInfo& other) const {
        if (d != other.d) return d < other.d;
        if (sum_nd != other.sum_nd) return sum_nd < other.sum_nd;
        return sum_sq_nd < other.sum_sq_nd;
    }
};

void initialize() {
    // Reconstruct adjacency list for G1 solely for initialization metrics
    vector<vector<int>> list1(n + 1);
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (adj1[i][j]) {
                list1[i].push_back(j);
            }
        }
    }

    // Helper to compute vertex invariants
    auto compute_info = [&](int id, const vector<int>& adj, const int* degrees) {
        long long s = 0;
        long long s_sq = 0;
        for (int neighbor : adj) {
            int d = degrees[neighbor];
            s += d;
            s_sq += (long long)d * d;
        }
        return VertexInfo{id, degrees[id], s, s_sq};
    };

    vector<VertexInfo> info1(n), info2(n);
    for (int i = 1; i <= n; ++i) {
        info1[i-1] = compute_info(i, list1[i], deg1);
        info2[i-1] = compute_info(i, adj2[i], deg2);
    }

    // Sort vertices by invariants
    sort(info1.begin(), info1.end());
    sort(info2.begin(), info2.end());

    // Initial mapping: map k-th sorted vertex of G2 to k-th sorted vertex of G1
    for (int k = 0; k < n; ++k) {
        p[info2[k].id] = info1[k].id;
    }
}

int calculate_score() {
    int matches = 0;
    for (int u = 1; u <= n; ++u) {
        for (int v : adj2[u]) {
            if (u < v) { 
                if (adj1[p[u]][p[v]]) {
                    matches++;
                }
            }
        }
    }
    return matches;
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    // Initialize adj1
    for(int i=0; i<=n; ++i)
        for(int j=0; j<=n; ++j)
            adj1[i][j] = false;

    // Read G1
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj1[u][v] = adj1[v][u] = true;
        deg1[u]++;
        deg1[v]++;
    }

    // Read G2
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
        deg2[u]++;
        deg2[v]++;
    }

    // Smart Greedy Initialization
    initialize();

    int current_score = calculate_score();
    for(int i=1; i<=n; ++i) best_p[i] = p[i];
    int best_score = current_score;

    // Simulated Annealing
    double start_time = get_time();
    double time_limit = 1.95; // Limit to slightly under 2 seconds
    
    // Temperature parameters
    double t_initial = 1.0;
    double t_final = 0.001;
    double temp = t_initial;

    const int CHECK_MASK = 1023; // Check time every 1024 iterations
    long long iter = 0;
    
    uniform_int_distribution<int> dist_n(1, n);
    uniform_real_distribution<double> dist_real(0.0, 1.0);

    while (true) {
        // Time management and temperature update
        if ((iter & CHECK_MASK) == 0) {
            double curr_time = get_time();
            if (curr_time - start_time > time_limit) break;
            double progress = (curr_time - start_time) / time_limit;
            temp = t_initial * pow(t_final / t_initial, progress);
        }
        iter++;

        // Pick two distinct vertices to swap in G2
        int u = dist_n(rng);
        int v = dist_n(rng);
        while (u == v) {
            v = dist_n(rng);
        }

        // Calculate delta efficiently
        // We propose swapping mappings: p[u] and p[v]
        int pu = p[u];
        int pv = p[v];
        int delta = 0;

        // Check edges incident to u (excluding v)
        // Edge (u, neighbor) in G2 currently maps to (pu, p[neighbor])
        // Will map to (pv, p[neighbor])
        for (int neighbor : adj2[u]) {
            if (neighbor == v) continue;
            int pn = p[neighbor];
            delta += (adj1[pv][pn] - adj1[pu][pn]);
        }

        // Check edges incident to v (excluding u)
        // Edge (v, neighbor) in G2 currently maps to (pv, p[neighbor])
        // Will map to (pu, p[neighbor])
        for (int neighbor : adj2[v]) {
            if (neighbor == u) continue;
            int pn = p[neighbor];
            delta += (adj1[pu][pn] - adj1[pv][pn]);
        }
        
        // Note: The edge (u, v) itself contributes equally before and after (undirected),
        // so it cancels out and is correctly skipped by the checks above.

        // Acceptance criteria
        bool accept = false;
        if (delta >= 0) {
            accept = true;
        } else {
            if (dist_real(rng) < exp(delta / temp)) {
                accept = true;
            }
        }

        if (accept) {
            swap(p[u], p[v]);
            current_score += delta;
            if (current_score > best_score) {
                best_score = current_score;
                for(int i=1; i<=n; ++i) best_p[i] = p[i];
                if (best_score == m) break; // Perfect match found
            }
        }
    }

    // Output result
    for (int i = 1; i <= n; ++i) {
        cout << best_p[i] << (i == n ? "" : " ");
    }
    cout << endl;

    return 0;
}