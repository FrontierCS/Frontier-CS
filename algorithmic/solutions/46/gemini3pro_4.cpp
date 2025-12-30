#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>

using namespace std;

// Structure to represent an operation
struct Operation {
    int machine;
    int duration;
};

int J, M;
vector<vector<Operation>> jobs;

// Global workspace vectors to avoid repeated allocations in evaluate
vector<int> job_idx_counters;
vector<long long> machine_ready;
vector<long long> job_ready;

// Function to evaluate the makespan of a given permutation of operations
// The permutation contains each job index 0..J-1 exactly M times.
long long evaluate(const vector<int>& perm) {
    // Reset workspace
    fill(job_idx_counters.begin(), job_idx_counters.end(), 0);
    fill(machine_ready.begin(), machine_ready.end(), 0);
    fill(job_ready.begin(), job_ready.end(), 0);

    for (int job : perm) {
        int op_idx = job_idx_counters[job];
        const Operation& op = jobs[job][op_idx];
        int m = op.machine;
        int dur = op.duration;
        
        // The operation can start when both the machine is free and the job's previous op is done
        long long start_time = max(machine_ready[m], job_ready[job]);
        long long end_time = start_time + dur;
        
        // Update availability
        machine_ready[m] = end_time;
        job_ready[job] = end_time;
        job_idx_counters[job]++;
    }

    // Makespan is the maximum completion time
    long long makespan = 0;
    for (long long t : job_ready) {
        if (t > makespan) makespan = t;
    }
    return makespan;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> J >> M)) return 0;

    jobs.resize(J);
    for (int i = 0; i < J; ++i) {
        jobs[i].resize(M);
        for (int k = 0; k < M; ++k) {
            cin >> jobs[i][k].machine >> jobs[i][k].duration;
        }
    }

    // Resize workspace vectors
    job_idx_counters.resize(J);
    machine_ready.resize(M);
    job_ready.resize(J);

    // Initial Solution Generation
    // We start with an interleaved sequence: 0, 1, ..., J-1, 0, 1, ...
    // This tends to be better than random or sequential for JSSP
    vector<int> current_perm;
    current_perm.reserve(J * M);
    for (int k = 0; k < M; ++k) {
        for (int i = 0; i < J; ++i) {
            current_perm.push_back(i);
        }
    }

    long long current_makespan = evaluate(current_perm);
    vector<int> best_perm = current_perm;
    long long best_makespan = current_makespan;

    // Setup Random Number Generation
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Try a few random shuffles to see if we can get a better starting point
    for(int i = 0; i < 10; ++i) {
        vector<int> temp = current_perm;
        shuffle(temp.begin(), temp.end(), rng);
        long long val = evaluate(temp);
        if (val < best_makespan) {
            best_makespan = val;
            best_perm = temp;
        }
    }

    // Initialize SA with the best found so far
    current_perm = best_perm;
    current_makespan = best_makespan;

    // Time Control
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.9; // Limit execution to just under 2 seconds

    // SA Parameters
    double T_initial = (double)best_makespan * 0.2; 
    if (T_initial < 1.0) T_initial = 1.0;
    double T = T_initial;
    double cooling_rate = 0.9997; 

    uniform_int_distribution<int> dist(0, J * M - 1);
    uniform_real_distribution<double> prob_dist(0.0, 1.0);

    long long iter = 0;
    while (true) {
        // Check time every 1024 iterations
        if ((iter & 1023) == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if (elapsed > time_limit) break;
            
            // Reheating strategy: if T drops too low, reset it to a fraction of initial
            if (T < 0.01) {
                T = T_initial * 0.1; 
            }
        }
        iter++;

        // Neighborhood move: swap two operations in the permutation
        int idx1 = dist(rng);
        int idx2 = dist(rng);
        if (idx1 == idx2) continue;

        swap(current_perm[idx1], current_perm[idx2]);
        long long new_makespan = evaluate(current_perm);

        bool accept = false;
        if (new_makespan < current_makespan) {
            accept = true;
            if (new_makespan < best_makespan) {
                best_makespan = new_makespan;
                best_perm = current_perm;
            }
        } else {
            // Metropolis criterion
            double delta = (double)(new_makespan - current_makespan);
            if (prob_dist(rng) < exp(-delta / T)) {
                accept = true;
            }
        }

        if (accept) {
            current_makespan = new_makespan;
        } else {
            // Revert swap
            swap(current_perm[idx1], current_perm[idx2]);
        }

        T *= cooling_rate;
    }

    // Reconstruct the machine orders from the best permutation found
    vector<vector<int>> machine_orders(M);
    fill(job_idx_counters.begin(), job_idx_counters.end(), 0);
    
    for (int job : best_perm) {
        int op_idx = job_idx_counters[job];
        const Operation& op = jobs[job][op_idx];
        machine_orders[op.machine].push_back(job);
        job_idx_counters[job]++;
    }

    // Output results
    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < J; ++i) {
            cout << machine_orders[m][i] << (i == J - 1 ? "" : " ");
        }
        cout << "\n";
    }

    return 0;
}