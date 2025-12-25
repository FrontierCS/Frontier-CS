#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>
#include <climits>

using namespace std;

// Global Inputs
int J, M;
struct Operation {
    int machine;
    int duration;
};
vector<vector<Operation>> jobs;
int total_ops;

// Best Solution
long long best_makespan = -1;
vector<vector<int>> best_machine_orders;

// Random Number Generator
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Evaluator
// Returns makespan of the schedule derived from permutation p.
// If update_best is true, it updates the global best_machine_orders if this solution is the best seen so far.
long long evaluate(const vector<int>& p, bool update_best) {
    // Static buffers to avoid reallocation
    static vector<int> job_op_idx;
    static vector<long long> job_avail_time;
    static vector<long long> machine_avail_time;
    
    if (job_op_idx.size() != (size_t)J) {
        job_op_idx.resize(J);
        job_avail_time.resize(J);
        machine_avail_time.resize(M);
    }
    
    // Reset state for new evaluation
    fill(job_op_idx.begin(), job_op_idx.end(), 0);
    fill(job_avail_time.begin(), job_avail_time.end(), 0);
    fill(machine_avail_time.begin(), machine_avail_time.end(), 0);
    
    static vector<vector<int>> current_machine_orders;
    if (update_best) {
        if (current_machine_orders.size() != (size_t)M) current_machine_orders.resize(M);
        for(int m=0; m<M; ++m) current_machine_orders[m].clear();
    }
    
    // Decode permutation to schedule (Semi-Active Schedule Construction)
    for (int job_id : p) {
        int k = job_op_idx[job_id];
        const Operation& op = jobs[job_id][k];
        int m = op.machine;
        int dur = op.duration;
        
        long long start_time = max(job_avail_time[job_id], machine_avail_time[m]);
        long long finish_time = start_time + dur;
        
        job_avail_time[job_id] = finish_time;
        machine_avail_time[m] = finish_time;
        job_op_idx[job_id]++;
        
        if (update_best) {
            current_machine_orders[m].push_back(job_id);
        }
    }
    
    long long makespan = 0;
    for (long long t : machine_avail_time) {
        if (t > makespan) makespan = t;
    }
    
    if (update_best) {
        if (best_makespan == -1 || makespan <= best_makespan) {
            best_makespan = makespan;
            best_machine_orders = current_machine_orders;
        }
    }
    
    return makespan;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> J >> M)) return 0;
    
    jobs.resize(J);
    total_ops = J * M;
    
    for (int i = 0; i < J; ++i) {
        jobs[i].resize(M);
        for (int k = 0; k < M; ++k) {
            cin >> jobs[i][k].machine >> jobs[i][k].duration;
        }
    }
    
    // Initial Permutation: Simply all jobs in order, repeated. Then shuffled.
    vector<int> p(total_ops);
    int idx = 0;
    for (int k = 0; k < M; ++k) {
        for (int i = 0; i < J; ++i) p[idx++] = i;
    }
    shuffle(p.begin(), p.end(), rng);
    
    // Initialize Best with the random start
    long long current_makespan = evaluate(p, true);
    vector<int> current_p = p;
    
    // Simulated Annealing Parameters
    // Estimate initial temperature by sampling some random moves
    double initial_temp = 0;
    double sum_diff = 0;
    int accepted_sample = 0;
    for(int i=0; i<500; ++i) {
        int u = uniform_int_distribution<int>(0, total_ops - 1)(rng);
        int v = uniform_int_distribution<int>(0, total_ops - 1)(rng);
        if (u == v) continue;
        swap(current_p[u], current_p[v]);
        long long val = evaluate(current_p, false);
        long long diff = val - current_makespan;
        if (diff > 0) {
            sum_diff += diff;
            accepted_sample++;
        }
        swap(current_p[u], current_p[v]); // revert
    }
    if (accepted_sample > 0) initial_temp = (sum_diff / accepted_sample);
    else initial_temp = max(1.0, (double)current_makespan * 0.01);
    
    // Reset current_p to initial random state
    current_p = p; 
    
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.90; // seconds, keeping a small buffer
    double temp = initial_temp;
    
    // Window size for localized swaps
    int w_size = max(2, total_ops / 5);
    
    long long iter = 0;
    while(true) {
        iter++;
        // Check time every 512 iterations to reduce overhead
        if ((iter & 511) == 0) {
            chrono::duration<double> elapsed = chrono::steady_clock::now() - start_time;
            if (elapsed.count() > time_limit) break;
            
            // Linear cooling schedule
            temp = initial_temp * (1.0 - elapsed.count() / time_limit);
            if (temp < 1e-5) temp = 1e-5;
        }
        
        // Generate neighbor: Swap u and v
        int u = uniform_int_distribution<int>(0, total_ops - 1)(rng);
        int v;
        // Bias towards swapping close elements to preserve structure
        if (uniform_real_distribution<double>(0,1)(rng) < 0.6) {
            int low = max(0, u - w_size);
            int high = min(total_ops - 1, u + w_size);
            v = uniform_int_distribution<int>(low, high)(rng);
        } else {
            v = uniform_int_distribution<int>(0, total_ops - 1)(rng);
        }
        
        if (u == v) continue;
        
        swap(current_p[u], current_p[v]);
        long long new_ms = evaluate(current_p, false);
        
        bool accept = false;
        if (new_ms <= current_makespan) {
            accept = true;
        } else {
            // Metropolis criterion
            double prob = exp(- (double)(new_ms - current_makespan) / temp);
            if (uniform_real_distribution<double>(0,1)(rng) < prob) accept = true;
        }
        
        if (accept) {
            current_makespan = new_ms;
            if (new_ms < best_makespan) {
                evaluate(current_p, true); // Record new global best
            }
        } else {
            swap(current_p[u], current_p[v]); // Revert move
        }
    }
    
    // Output the best machine orders found
    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < J; ++i) {
            cout << best_machine_orders[m][i] << (i == J - 1 ? "" : " ");
        }
        cout << "\n";
    }
    
    return 0;
}