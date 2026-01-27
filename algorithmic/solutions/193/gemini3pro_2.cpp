#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <chrono>
#include <cstdlib>

using namespace std;

// Clause structure to store simplified clauses
struct Clause {
    int l1, l2; // Literals stored as raw integers from input
    int size;   // 0 (tautology), 1 (single literal), or 2 (two literals)
};

const int MAXN = 1005;
const int MAXM = 40005;

int n, m;
vector<Clause> clauses;
// adj[v][req]: list of clause indices where variable v is required to be req (0 or 1)
// req=1 means positive literal (x), req=0 means negative literal (-x)
vector<int> adj[MAXN][2]; 

int assignment[MAXN];
int sat_count[MAXM]; // Number of satisfied literals in each clause
int best_assignment[MAXN];

// Fast RNG using xorshift64
uint64_t rng_state = 123456789;
inline uint64_t xorshift() {
    uint64_t x = rng_state;
    x ^= x << 13;
    x ^= x >> 7;
    x ^= x << 17;
    return rng_state = x;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    int tautologies = 0;
    clauses.reserve(m);

    // Read and preprocess clauses
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        
        int var_u = abs(u);
        int req_u = (u > 0 ? 1 : 0);
        int var_v = abs(v);
        int req_v = (v > 0 ? 1 : 0);

        if (var_u == var_v) {
            if (req_u != req_v) {
                // Tautology (x or -x), always satisfied
                tautologies++;
                clauses.push_back({0, 0, 0});
            } else {
                // Duplicate (x or x) -> effectively (x)
                clauses.push_back({u, 0, 1});
                adj[var_u][req_u].push_back(i);
            }
        } else {
            // Standard clause (x or y)
            clauses.push_back({u, v, 2});
            adj[var_u][req_u].push_back(i);
            adj[var_v][req_v].push_back(i);
        }
    }

    // Initial random assignment
    for (int i = 1; i <= n; ++i) {
        assignment[i] = (xorshift() & 1);
    }

    // Compute initial score and sat_counts
    int current_sat = tautologies;
    for (int i = 0; i < m; ++i) {
        if (clauses[i].size == 0) continue;
        
        int c_sat = 0;
        
        // Check Literal 1
        int u = clauses[i].l1;
        if (assignment[abs(u)] == (u > 0 ? 1 : 0)) c_sat++;
        
        // Check Literal 2
        if (clauses[i].size == 2) {
            int v = clauses[i].l2;
            if (assignment[abs(v)] == (v > 0 ? 1 : 0)) c_sat++;
        }
        
        sat_count[i] = c_sat;
        if (c_sat > 0) current_sat++;
    }

    int best_sat = current_sat;
    for (int i = 1; i <= n; ++i) best_assignment[i] = assignment[i];

    // Simulated Annealing
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.85; // seconds, typical limit is 2s
    double T = 1.0; // Starting temperature
    
    int iter = 0;
    const int check_interval = 4096;

    while (true) {
        // Time check and Temp update periodically
        if ((iter & (check_interval - 1)) == 0) {
            auto curr_time = chrono::steady_clock::now();
            chrono::duration<double> elapsed = curr_time - start_time;
            if (elapsed.count() > time_limit) break;
            
            double ratio = elapsed.count() / time_limit;
            T = 1.0 * (1.0 - ratio); 
            if (T < 0.005) T = 0.005;
        }

        // Pick a random variable to flip
        int v = (xorshift() % n) + 1;
        int old_val = assignment[v];
        int new_val = 1 - old_val; 
        
        int delta = 0;

        // Losing clauses: clauses requiring the old value of v
        // The literal corresponding to v will flip True -> False
        const vector<int> &losing = adj[v][old_val];
        for (int idx : losing) {
            // If satisfied count drops from 1 to 0, clause becomes unsatisfied
            if (sat_count[idx] == 1) delta--;
        }

        // Gaining clauses: clauses requiring the new value of v
        // The literal corresponding to v will flip False -> True
        const vector<int> &gaining = adj[v][new_val];
        for (int idx : gaining) {
            // If satisfied count rises from 0 to 1, clause becomes satisfied
            if (sat_count[idx] == 0) delta++;
        }

        // Acceptance criteria
        bool accept = (delta >= 0);
        if (!accept) {
             // Accept worse moves with probability exp(delta / T)
             if (delta > -15) { 
                 double prob = exp(delta / T);
                 // Convert random uint64 to double [0, 1]
                 if ((xorshift() * 5.421010862427522e-20) < prob) accept = true;
             }
        }

        if (accept) {
            // Apply changes
            assignment[v] = new_val;
            current_sat += delta;
            
            // Update counts
            for (int idx : losing) sat_count[idx]--;
            for (int idx : gaining) sat_count[idx]++;
            
            // Track best solution
            if (current_sat > best_sat) {
                best_sat = current_sat;
                for (int i = 1; i <= n; ++i) best_assignment[i] = assignment[i];
                if (best_sat == m) break; // Optimization achieved
            }
        }
        
        iter++;
    }

    // Output result
    for (int i = 1; i <= n; ++i) {
        cout << best_assignment[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}