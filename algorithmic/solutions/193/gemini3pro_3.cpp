#include <iostream>
#include <vector>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Fast I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

struct Clause {
    int l1, l2;
};

int n, m;
vector<Clause> clauses;
// var_occ[1][v] stores indices of clauses containing literal v (positive occurrence)
// var_occ[0][v] stores indices of clauses containing literal -v (negative occurrence)
vector<vector<int>> var_occ[2];

int current_assignment[1005];
int sat_count[40005]; // number of true literals in each clause
int total_satisfied = 0;

int best_assignment[1005];
int max_satisfied = -1;

inline int get_sat_val(int lit) {
    if (lit > 0) return current_assignment[lit];
    else return 1 - current_assignment[-lit];
}

void init_random() {
    total_satisfied = 0;
    // Generate a random assignment
    for (int i = 1; i <= n; ++i) {
        current_assignment[i] = rand() % 2;
    }
    // Calculate satisfied clauses
    for (int i = 0; i < m; ++i) {
        sat_count[i] = get_sat_val(clauses[i].l1) + get_sat_val(clauses[i].l2);
        if (sat_count[i] > 0) total_satisfied++;
    }
    // Update best found so far
    if (total_satisfied > max_satisfied) {
        max_satisfied = total_satisfied;
        for (int i = 1; i <= n; ++i) best_assignment[i] = current_assignment[i];
    }
}

int main() {
    fast_io();
    srand(time(0));

    if (!(cin >> n >> m)) return 0;

    var_occ[0].resize(n + 1);
    var_occ[1].resize(n + 1);
    clauses.reserve(m);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        clauses.push_back({u, v});
        
        if (u > 0) var_occ[1][u].push_back(i);
        else var_occ[0][-u].push_back(i);
        
        if (v > 0) var_occ[1][v].push_back(i);
        else var_occ[0][-v].push_back(i);
    }

    // Edge case: no clauses
    if (m == 0) {
        for (int i = 1; i <= n; ++i) cout << "0" << (i == n ? "" : " ");
        cout << "\n";
        return 0;
    }

    init_random();

    // Use Simulated Annealing with time limit
    auto start_time = chrono::steady_clock::now();
    double time_limit = 0.95; // Seconds

    mt19937 rng(1337); 
    uniform_int_distribution<int> dist_var(1, n);
    uniform_real_distribution<double> dist_prob(0.0, 1.0);

    double t = 2.0;
    int iter = 0;

    while (true) {
        // Check time every 4096 iterations to reduce overhead
        if ((iter & 4095) == 0) {
            auto curr_time = chrono::steady_clock::now();
            chrono::duration<double> elapsed = curr_time - start_time;
            if (elapsed.count() > time_limit) break;
        }

        int v = dist_var(rng);
        
        // Calculate the change in satisfied clauses (delta) if we flip variable v
        int delta = 0;
        int current_val = current_assignment[v];
        
        // 'losing' clauses: those where the literal corresponding to v's current value appears.
        // These literals will become FALSE.
        const vector<int> &losing = (current_val == 1) ? var_occ[1][v] : var_occ[0][v];
        
        // 'gaining' clauses: those where the literal corresponding to v's new value appears.
        // These literals will become TRUE.
        const vector<int> &gaining = (current_val == 1) ? var_occ[0][v] : var_occ[1][v];

        // If a clause has sat_count == 1 and is in 'losing', it becomes UNSAT (count 0). Delta -1.
        for (int idx : losing) {
            if (sat_count[idx] == 1) delta--;
        }
        // If a clause has sat_count == 0 and is in 'gaining', it becomes SAT (count 1). Delta +1.
        for (int idx : gaining) {
            if (sat_count[idx] == 0) delta++;
        }

        // Acceptance criterion
        bool accept = false;
        if (delta >= 0) {
            accept = true;
        } else {
            // Metropolis criterion: accept with probability exp(delta / T)
            if (dist_prob(rng) < exp(delta / t)) {
                accept = true;
            }
        }

        if (accept) {
            // Perform the flip
            current_assignment[v] = 1 - current_val;
            
            for (int idx : losing) {
                sat_count[idx]--;
                if (sat_count[idx] == 0) total_satisfied--;
            }
            for (int idx : gaining) {
                sat_count[idx]++;
                if (sat_count[idx] == 1) total_satisfied++;
            }

            // Update global best
            if (total_satisfied > max_satisfied) {
                max_satisfied = total_satisfied;
                for (int i = 1; i <= n; ++i) best_assignment[i] = current_assignment[i];
                if (max_satisfied == m) break; // Found optimal
            }
        }

        // Cooling schedule
        t *= 0.9995;
        // Reheat if temperature gets too low to escape local optima
        if (t < 0.15) t = 2.0; 
        iter++;
    }

    // Output the best assignment found
    for (int i = 1; i <= n; ++i) {
        cout << best_assignment[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}