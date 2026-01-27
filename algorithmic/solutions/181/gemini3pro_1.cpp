#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <ctime>
#include <random>
#include <cstring>

using namespace std;

// Maximum N as per problem statement
const int MAXN = 2005;

// Matrices and adjacency lists
// Using signed char for small memory footprint (0 or 1)
int8_t D[MAXN][MAXN];
int8_t F[MAXN][MAXN];

// Adjacency lists for sparse iteration over Flow matrix
vector<int> F_out[MAXN];
vector<int> F_in[MAXN];

// Permutation: p[i] = location assigned to facility i
int p[MAXN];

int n;

// Calculate total cost for a permutation from scratch
// O(N^2)
long long calculate_total_cost() {
    long long cost = 0;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (F[i][j]) {
                if (D[p[i]][p[j]]) {
                    cost++;
                }
            }
        }
    }
    return cost;
}

// Calculate delta cost for swapping facilities u and v
// p is the current permutation
// L_u = p[u] (current location of u), L_v = p[v] (current location of v)
// The proposed move is to swap these locations: new_p[u] = L_v, new_p[v] = L_u.
// O(deg(u) + deg(v))
int calculate_delta(int u, int v) {
    int L_u = p[u];
    int L_v = p[v];
    
    int delta = 0;
    
    // 1. Cross terms between u and v, and self-loops
    // Subtract Old contributions
    if (F[u][v] && D[L_u][L_v]) delta -= 1;
    if (F[v][u] && D[L_v][L_u]) delta -= 1;
    if (F[u][u] && D[L_u][L_u]) delta -= 1;
    if (F[v][v] && D[L_v][L_v]) delta -= 1;
    
    // Add New contributions (u is at L_v, v is at L_u)
    if (F[u][v] && D[L_v][L_u]) delta += 1;
    if (F[v][u] && D[L_u][L_v]) delta += 1;
    if (F[u][u] && D[L_v][L_v]) delta += 1;
    if (F[v][v] && D[L_u][L_u]) delta += 1;
    
    // 2. Outgoing edges from u (to k != u, v)
    // For neighbor k, flow F[u][k] is moved from dist(L_u, p[k]) to dist(L_v, p[k])
    for (int k : F_out[u]) {
        if (k == u || k == v) continue;
        int pk = p[k];
        delta += (D[L_v][pk] - D[L_u][pk]);
    }
    
    // 3. Outgoing edges from v (to k != u, v)
    // Flow F[v][k] moved from dist(L_v, p[k]) to dist(L_u, p[k])
    for (int k : F_out[v]) {
        if (k == u || k == v) continue;
        int pk = p[k];
        delta += (D[L_u][pk] - D[L_v][pk]);
    }
    
    // 4. Incoming edges to u (from k != u, v)
    // Flow F[k][u] moved from dist(p[k], L_u) to dist(p[k], L_v)
    for (int k : F_in[u]) {
        if (k == u || k == v) continue;
        int pk = p[k];
        delta += (D[pk][L_v] - D[pk][L_u]);
    }

    // 5. Incoming edges to v (from k != u, v)
    // Flow F[k][v] moved from dist(p[k], L_v) to dist(p[k], L_u)
    for (int k : F_in[v]) {
        if (k == u || k == v) continue;
        int pk = p[k];
        delta += (D[pk][L_u] - D[pk][L_v]);
    }
    
    return delta;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    // Read Distance Matrix D
    // degD: sum of row + col for each location
    vector<int> degD(n, 0);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int val; cin >> val;
            D[i][j] = (int8_t)val;
            if (val) {
                degD[i]++;
                degD[j]++;
            }
        }
    }

    // Read Flow Matrix F
    // degF: sum of row + col for each facility
    vector<int> degF(n, 0);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int val; cin >> val;
            F[i][j] = (int8_t)val;
            if (val) {
                degF[i]++;
                degF[j]++;
                F_out[i].push_back(j);
                F_in[j].push_back(i);
            }
        }
    }

    // Initial Solution Construction: Greedy Heuristic
    // We want to minimize cost = sum(F * D).
    // Strategy: Map facilities with high flow (high degree) to locations with low connectivity (low degree).
    
    vector<int> sortedF(n);
    iota(sortedF.begin(), sortedF.end(), 0);
    // Sort facilities by degree descending
    sort(sortedF.begin(), sortedF.end(), [&](int a, int b) {
        return degF[a] > degF[b];
    });

    vector<int> sortedD(n);
    iota(sortedD.begin(), sortedD.end(), 0);
    // Sort locations by degree ascending
    sort(sortedD.begin(), sortedD.end(), [&](int a, int b) {
        return degD[a] < degD[b];
    });

    // Assign based on sorted order
    for (int i = 0; i < n; ++i) {
        p[sortedF[i]] = sortedD[i];
    }

    long long current_cost = calculate_total_cost();
    
    // Simulated Annealing
    // Aim for ~1.85 seconds to fit within standard 2s limit
    double time_limit = 1.85; 
    clock_t start_time = clock();
    
    mt19937 rng(1337);
    
    // Keep track of best solution
    vector<int> best_p(n);
    for(int i=0; i<n; ++i) best_p[i] = p[i];
    long long best_cost = current_cost;

    // Annealing parameters
    double t_start = 2.0; 
    double t_end = 0.002;
    
    int iter = 0;
    
    while (true) {
        iter++;
        // Batched time check to reduce overhead
        if ((iter & 4095) == 0) { 
            double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
            if (elapsed > time_limit) break;
        }

        // Pick two distinct facilities at random
        int u = rng() % n;
        int v = rng() % n;
        while (u == v) {
            v = rng() % n;
        }

        // Calculate cost difference
        int delta = calculate_delta(u, v);
        
        bool accept = false;
        if (delta <= 0) {
            accept = true; // Always accept improvement or neutral moves
        } else {
            // Probabilistic acceptance
            double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
            // Linear interpolation of temperature on log scale (exponential cooling)
            double temp = t_start * pow(t_end / t_start, elapsed / time_limit);
            
            if (bernoulli_distribution(exp(-delta / temp))(rng)) {
                accept = true;
            }
        }

        if (accept) {
            // Perform swap
            swap(p[u], p[v]);
            current_cost += delta;
            
            // Update best solution
            if (current_cost < best_cost) {
                best_cost = current_cost;
                for(int i=0; i<n; ++i) best_p[i] = p[i];
            }
        }
    }

    // Output result
    // Output format requires 1-based indexing for locations
    for (int i = 0; i < n; ++i) {
        cout << best_p[i] + 1 << (i == n - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}