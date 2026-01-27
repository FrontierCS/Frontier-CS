#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <cmath>
#include <chrono>

using namespace std;

// Global data to handle N=2000 efficiently
const int MAXN = 2005;
bool adj1[MAXN][MAXN]; // Adjacency matrix for G1 (Target)
vector<int> adj2[MAXN]; // Adjacency list for G2 (Source)
int p[MAXN]; // Mapping from G2 vertices to G1 vertices
int best_p[MAXN];
int deg1[MAXN];
int deg2[MAXN];
int n, m;

// Fast Random Number Generator
struct Xorshift {
    unsigned int x = 123456789;
    unsigned int y = 362436069;
    unsigned int z = 521288629;
    unsigned int w = 88675123;
    
    inline unsigned int next() {
        unsigned int t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = w ^ (w >> 19) ^ (t ^ (t >> 8));
    }
    
    inline int next(int max_val) { // returns integer in [0, max_val]
        return next() % (max_val + 1);
    }
    
    inline double nextDouble() {
        return next() * 2.3283064365386963e-10; // Multiply by 1/2^32
    }
} rng;

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    // Read G1 edges
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v; // Convert to 0-based
        adj1[u][v] = adj1[v][u] = true;
        deg1[u]++;
        deg1[v]++;
    }

    // Read G2 edges
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v; // Convert to 0-based
        adj2[u].push_back(v);
        adj2[v].push_back(u);
        deg2[u]++;
        deg2[v]++;
    }

    // Initial solution heuristic: Sort vertices by degree
    // Map high-degree vertices in G2 to high-degree vertices in G1
    vector<int> nodes1(n), nodes2(n);
    iota(nodes1.begin(), nodes1.end(), 0);
    iota(nodes2.begin(), nodes2.end(), 0);

    sort(nodes1.begin(), nodes1.end(), [&](int a, int b) {
        return deg1[a] > deg1[b];
    });
    sort(nodes2.begin(), nodes2.end(), [&](int a, int b) {
        return deg2[a] > deg2[b];
    });

    for (int i = 0; i < n; ++i) {
        p[nodes2[i]] = nodes1[i];
    }

    // Calculate initial score (number of matched edges)
    long long current_matches = 0;
    for (int u = 0; u < n; ++u) {
        for (int v : adj2[u]) {
            if (u < v) { // Count undirected edges once
                if (adj1[p[u]][p[v]]) {
                    current_matches++;
                }
            }
        }
    }

    // Initialize best solution found so far
    long long best_matches = current_matches;
    for (int i = 0; i < n; ++i) best_p[i] = p[i];

    // Simulated Annealing
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.95; // seconds
    
    // Parameters
    double t_start = 1.0;
    double t_end = 1e-4;
    double temp = t_start;
    
    int iter = 0;
    int check_interval = 1023; // Check time every 1024 iterations

    while (true) {
        iter++;
        
        // Time control and cooling schedule
        if ((iter & check_interval) == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if (elapsed > time_limit) break;
            
            // Linear cooling
            temp = t_start * (1.0 - elapsed / time_limit);
            if (temp < t_end) temp = t_end;
        }

        // Pick two distinct vertices u, v in G2 to swap their mappings
        int u = rng.next(n - 1);
        int v = rng.next(n - 1);
        if (u == v) v = (u + 1) % n;

        int pu = p[u];
        int pv = p[v];

        // Calculate change in score (delta)
        // We are proposing to map u -> pv and v -> pu
        long long delta = 0;

        // Check edges incident to u in G2
        for (int w : adj2[u]) {
            if (w == v) continue; // Edge (u, v) contribution doesn't change
            int pw = p[w];
            // Old: u->pu, w->pw. Check edge (pu, pw) in G1
            bool has_old = adj1[pu][pw];
            // New: u->pv, w->pw. Check edge (pv, pw) in G1
            bool has_new = adj1[pv][pw];
            
            if (has_old != has_new) {
                delta += (has_new ? 1 : -1);
            }
        }

        // Check edges incident to v in G2
        for (int w : adj2[v]) {
            if (w == u) continue;
            int pw = p[w];
            // Old: v->pv, w->pw. Check edge (pv, pw) in G1
            bool has_old = adj1[pv][pw];
            // New: v->pu, w->pw. Check edge (pu, pw) in G1
            bool has_new = adj1[pu][pw];
            
            if (has_old != has_new) {
                delta += (has_new ? 1 : -1);
            }
        }

        // Metropolis acceptance criterion
        bool accept = false;
        if (delta >= 0) {
            accept = true;
        } else {
            if (rng.nextDouble() < exp(delta / temp)) {
                accept = true;
            }
        }

        if (accept) {
            p[u] = pv;
            p[v] = pu;
            current_matches += delta;
            
            if (current_matches > best_matches) {
                best_matches = current_matches;
                for (int i = 0; i < n; ++i) best_p[i] = p[i];
            }
        }
    }

    // Output the best permutation found
    for (int i = 0; i < n; ++i) {
        cout << best_p[i] + 1 << (i == n - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}