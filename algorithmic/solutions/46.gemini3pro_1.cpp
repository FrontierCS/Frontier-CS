#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>
#include <numeric>

using namespace std;

// Global problem data
int J, M;
// Flattened arrays for performance: index = job_id * M + op_index
vector<int> job_route_flat;
vector<int> job_proc_flat;

// Function to evaluate the makespan of a permutation.
// The permutation p is a Bierwirth vector: a sequence of length J*M containing 
// exactly M copies of each job ID (0..J-1).
// This function assumes p is valid.
// It uses static vectors to avoid allocation overhead during the search.
long long evaluate_fast(const vector<int>& p) {
    // Static working arrays to reduce memory allocation overhead
    // Max constraints: J=50, M=25. Using slightly larger buffers.
    static vector<int> job_next_op_idx(60);
    static vector<long long> job_avail_time(60);
    static vector<long long> machine_avail_time(30);
    
    // Reset state for new evaluation
    // We only need to clear up to J and M
    fill(job_next_op_idx.begin(), job_next_op_idx.begin() + J, 0);
    fill(job_avail_time.begin(), job_avail_time.begin() + J, 0);
    fill(machine_avail_time.begin(), machine_avail_time.begin() + M, 0);
    
    long long makespan = 0;
    
    // Iterate through the permutation
    for (int job_id : p) {
        int op_idx = job_next_op_idx[job_id];
        
        // Retrieve operation details from flattened arrays
        int flat_idx = job_id * M + op_idx;
        int mach = job_route_flat[flat_idx];
        int dur = job_proc_flat[flat_idx];
        
        // Earliest start is max of when job is ready and when machine is free
        long long start_time = (job_avail_time[job_id] > machine_avail_time[mach]) ? 
                               job_avail_time[job_id] : machine_avail_time[mach];
        
        long long end_time = start_time + dur;
        
        // Update availability
        job_avail_time[job_id] = end_time;
        machine_avail_time[mach] = end_time;
        
        // Track global makespan
        if (end_time > makespan) makespan = end_time;
        
        // Advance job operation pointer
        job_next_op_idx[job_id]++;
    }
    return makespan;
}

// Full evaluation that also reconstructs the machine schedules for output
void construct_solution(const vector<int>& p, vector<vector<int>>& machine_orders) {
    vector<int> job_next_op_idx(J, 0);
    vector<long long> job_avail_time(J, 0);
    vector<long long> machine_avail_time(M, 0);
    
    for(int m=0; m<M; ++m) machine_orders[m].clear();
    
    for (int job_id : p) {
        int op_idx = job_next_op_idx[job_id];
        int flat_idx = job_id * M + op_idx;
        int mach = job_route_flat[flat_idx];
        int dur = job_proc_flat[flat_idx];
        
        long long start_time = max(job_avail_time[job_id], machine_avail_time[mach]);
        long long end_time = start_time + dur;
        
        job_avail_time[job_id] = end_time;
        machine_avail_time[mach] = end_time;
        
        // Record this job on the machine's schedule
        machine_orders[mach].push_back(job_id);
        
        job_next_op_idx[job_id]++;
    }
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> J >> M)) return 0;
    
    // Resize flattened arrays
    job_route_flat.resize(J * M);
    job_proc_flat.resize(J * M);
    
    long long total_processing_time = 0;
    
    // Read input
    for (int i = 0; i < J; ++i) {
        for (int k = 0; k < M; ++k) {
            int m, p;
            cin >> m >> p;
            int flat_idx = i * M + k;
            job_route_flat[flat_idx] = m;
            job_proc_flat[flat_idx] = p;
            total_processing_time += p;
        }
    }
    
    // Initial permutation: simple concatenation of jobs
    // Bierwirth representation: each job ID appears M times
    vector<int> current_p;
    current_p.reserve(J * M);
    for (int i = 0; i < J; ++i) {
        for (int k = 0; k < M; ++k) {
            current_p.push_back(i);
        }
    }
    
    // Random Number Generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    // Start with a random shuffle
    shuffle(current_p.begin(), current_p.end(), rng);
    
    long long current_score = evaluate_fast(current_p);
    vector<int> best_p = current_p;
    long long best_score = current_score;
    
    // Simulated Annealing Parameters
    // We aim for approx 1.9 seconds runtime to stay within common 2s limits safely
    double max_time_seconds = 1.9;
    auto start_time = chrono::steady_clock::now();
    
    // Initial temperature heuristic: based on average processing time
    // A swap might impact makespan by roughly the duration of an operation
    double avg_dur = (double)total_processing_time / (J * M);
    double initial_temp = avg_dur * 1.5; 
    double temp = initial_temp;
    
    // Cooling rate
    // We expect roughly 200k-500k iterations depending on machine speed
    // 0.99997^200000 ~= 0.002
    double cooling_rate = 0.99997;
    
    int iter = 0;
    int p_size = J * M;
    
    // Pre-allocate neighbor vector
    vector<int> neighbor_p = current_p;
    
    while (true) {
        // Time check every batch of iterations
        if ((iter & 511) == 0) {
            auto curr_time = chrono::steady_clock::now();
            chrono::duration<double> elapsed = curr_time - start_time;
            if (elapsed.count() > max_time_seconds) break;
            
            // Reheating mechanism if temperature drops too low but time remains
            if (temp < 0.1 && elapsed.count() < max_time_seconds * 0.8) {
                temp = initial_temp * 0.5;
            }
        }
        iter++;
        
        // Generate Neighbor
        // 50% chance Swap, 50% chance Insert
        // Insert is generally more powerful for scheduling
        int move_type = rng() & 1; 
        
        neighbor_p = current_p;
        
        if (move_type == 0) { 
            // Swap two distinct indices
            int idx1 = rng() % p_size;
            int idx2 = rng() % p_size;
            // Ensure distinct
            if (idx1 == idx2) idx2 = (idx1 + 1) % p_size;
            
            swap(neighbor_p[idx1], neighbor_p[idx2]);
        } else {
            // Insert (Shift)
            int idx1 = rng() % p_size; // From
            int idx2 = rng() % p_size; // To
            if (idx1 != idx2) {
                int val = neighbor_p[idx1];
                neighbor_p.erase(neighbor_p.begin() + idx1);
                neighbor_p.insert(neighbor_p.begin() + idx2, val);
            }
        }
        
        long long neighbor_score = evaluate_fast(neighbor_p);
        long long delta = neighbor_score - current_score;
        
        bool accept = false;
        if (delta <= 0) {
            accept = true;
        } else {
            // Metropolis criterion
            if (exp(-delta / temp) * 10000 > (rng() % 10000)) {
                accept = true;
            }
        }
        
        if (accept) {
            current_p = neighbor_p;
            current_score = neighbor_score;
            if (current_score < best_score) {
                best_score = current_score;
                best_p = current_p;
            }
        }
        
        temp *= cooling_rate;
    }
    
    // Output solution
    vector<vector<int>> machine_orders(M);
    construct_solution(best_p, machine_orders);
    
    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < J; ++i) {
            cout << machine_orders[m][i] << (i == J - 1 ? "" : " ");
        }
        cout << "\n";
    }
    
    return 0;
}