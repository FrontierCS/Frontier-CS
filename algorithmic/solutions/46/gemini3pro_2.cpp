#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <chrono>
#include <random>
#include <climits>

using namespace std;

// Data structures
struct Operation {
    int machine;
    int duration;
};

int J, M;
// Flattened jobs vector for better cache locality
// Layout: Job 0's M operations, Job 1's M operations, ...
vector<Operation> flat_jobs; 

vector<int> best_permutation;
int best_makespan = INT_MAX;

// Fast random number generator
struct Xorshift {
    unsigned int x = 123456789;
    unsigned int y = 362436069;
    unsigned int z = 521288629;
    unsigned int w = 88675123;
    unsigned int next() {
        unsigned int t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    }
    double next_double() {
        return (next() & 0xFFFFFF) / 16777216.0;
    }
    int next_int(int n) {
        return next() % n;
    }
} rng;

// Global working arrays to avoid reallocation in evaluate
vector<int> current_job_idx;
vector<int> job_avail;
vector<int> machine_avail;

int evaluate(const vector<int>& p) {
    fill(current_job_idx.begin(), current_job_idx.end(), 0);
    fill(job_avail.begin(), job_avail.end(), 0);
    fill(machine_avail.begin(), machine_avail.end(), 0);
    
    int current_makespan = 0;
    
    for (int job_id : p) {
        int op_idx = current_job_idx[job_id];
        current_job_idx[job_id]++;
        
        // Access flattened jobs array
        const Operation& op = flat_jobs[job_id * M + op_idx];
        
        int start_time = max(job_avail[job_id], machine_avail[op.machine]);
        int finish_time = start_time + op.duration;
        
        job_avail[job_id] = finish_time;
        machine_avail[op.machine] = finish_time;
        
        if (finish_time > current_makespan) {
            current_makespan = finish_time;
        }
    }
    return current_makespan;
}

void solve() {
    // A permutation of J * M job indices
    vector<int> p;
    p.reserve(J * M);
    for (int j = 0; j < J; ++j) {
        for (int m = 0; m < M; ++m) {
            p.push_back(j);
        }
    }
    
    current_job_idx.resize(J);
    job_avail.resize(J);
    machine_avail.resize(M);

    // Initial random solution
    mt19937 mt_rand(1337);
    shuffle(p.begin(), p.end(), mt_rand);
    
    vector<int> current_p = p;
    int current_makespan = evaluate(current_p);
    
    best_permutation = current_p;
    best_makespan = current_makespan;
    
    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 1.95; // seconds
    
    // Heuristic for initial temperature
    long long total_proc = 0;
    for(const auto& op : flat_jobs) total_proc += op.duration;
    double avg_proc = (double)total_proc / (J * M);
    
    double t_initial = avg_proc * 1.5; 
    if (t_initial < 1.0) t_initial = 1.0;
    
    double t_final = 0.01;
    double temp = t_initial;
    
    int iter = 0;
    int size = J * M;
    
    // Simulated Annealing
    while (true) {
        iter++;
        
        // Periodically check time and update temperature
        if ((iter & 1023) == 0) {
            auto now = chrono::high_resolution_clock::now();
            chrono::duration<double> elapsed = now - start_time;
            if (elapsed.count() > time_limit) break;
            
            double progress = elapsed.count() / time_limit;
            temp = t_initial * pow(t_final / t_initial, progress);
        }

        // Neighbor: swap two random indices
        int idx1 = rng.next_int(size);
        int idx2 = rng.next_int(size);
        
        if (idx1 == idx2 || current_p[idx1] == current_p[idx2]) continue;
        
        swap(current_p[idx1], current_p[idx2]);
        
        int new_makespan = evaluate(current_p);
        
        if (new_makespan < best_makespan) {
            best_makespan = new_makespan;
            best_permutation = current_p;
        }
        
        // Metropolis acceptance criteria
        if (new_makespan <= current_makespan) {
            current_makespan = new_makespan;
        } else {
            if (temp < 1e-6) {
                // Temperature too low, reject uphill moves
                swap(current_p[idx1], current_p[idx2]);
            } else {
                double delta = new_makespan - current_makespan;
                if (rng.next_double() < exp(-delta / temp)) {
                    current_makespan = new_makespan;
                } else {
                    swap(current_p[idx1], current_p[idx2]); // Revert
                }
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> J >> M)) return 0;
    
    flat_jobs.resize(J * M);
    for (int j = 0; j < J; ++j) {
        for (int m = 0; m < M; ++m) {
            cin >> flat_jobs[j * M + m].machine >> flat_jobs[j * M + m].duration;
        }
    }
    
    solve();
    
    // Reconstruct output from the best permutation found
    vector<vector<int>> machine_orders(M);
    
    // Use current_job_idx to track current operation index during reconstruction
    // Note: current_job_idx was resized in solve()
    fill(current_job_idx.begin(), current_job_idx.end(), 0);
    
    for (int job_id : best_permutation) {
        int op_idx = current_job_idx[job_id];
        current_job_idx[job_id]++;
        
        int m = flat_jobs[job_id * M + op_idx].machine;
        machine_orders[m].push_back(job_id);
    }
    
    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < machine_orders[m].size(); ++i) {
            cout << machine_orders[m][i] << (i == machine_orders[m].size() - 1 ? "" : " ");
        }
        cout << "\n";
    }
    
    return 0;
}