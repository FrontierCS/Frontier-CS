#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>
#include <climits>

using namespace std;

// Problem Data
int J, M;
struct Task {
    int machine;
    int time;
};
vector<vector<Task>> job_routes; // [job][op_index]

// Global helpers to avoid reallocation in the evaluation loop
vector<int> job_next_idx;
vector<long long> job_ready_time;
vector<long long> machine_ready_time;

// Evaluates the makespan of a given operation-based permutation
// perm: vector of size J*M containing job indices.
// Each job index appears M times.
long long get_makespan(const vector<int>& perm) {
    // Reset helper arrays
    fill(job_next_idx.begin(), job_next_idx.end(), 0);
    fill(job_ready_time.begin(), job_ready_time.end(), 0);
    fill(machine_ready_time.begin(), machine_ready_time.end(), 0);

    long long current_makespan = 0;

    for (int job : perm) {
        // Retrieve the specific operation for this occurrence of the job
        int op_idx = job_next_idx[job];
        const Task& task = job_routes[job][op_idx];
        int m = task.machine;
        int p = task.time;

        // Calculate earliest start time
        // Must wait for previous operation of the same job to finish
        // Must wait for the machine to be free
        long long start = max(job_ready_time[job], machine_ready_time[m]);
        long long end = start + p;

        // Update availability
        job_ready_time[job] = end;
        machine_ready_time[m] = end;
        job_next_idx[job]++;
        
        if (end > current_makespan) current_makespan = end;
    }
    return current_makespan;
}

// Decodes the permutation into machine orders and prints them
void print_solution(const vector<int>& perm) {
    vector<vector<int>> machine_orders(M);
    fill(job_next_idx.begin(), job_next_idx.end(), 0);

    for (int job : perm) {
        int op_idx = job_next_idx[job];
        int m = job_routes[job][op_idx].machine;
        machine_orders[m].push_back(job);
        job_next_idx[job]++;
    }

    for (int m = 0; m < M; ++m) {
        for (size_t i = 0; i < machine_orders[m].size(); ++i) {
            cout << machine_orders[m][i] << (i == machine_orders[m].size() - 1 ? "" : " ");
        }
        cout << "\n";
    }
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> J >> M)) return 0;

    job_routes.resize(J);
    for (int i = 0; i < J; ++i) {
        job_routes[i].reserve(M);
        for (int k = 0; k < M; ++k) {
            int m, p;
            cin >> m >> p;
            job_routes[i].push_back({m, p});
        }
    }

    // Resize global helpers
    job_next_idx.resize(J);
    job_ready_time.resize(J);
    machine_ready_time.resize(M);

    // Initial operation-based permutation: contain each job index M times
    vector<int> perm;
    perm.reserve(J * M);
    for (int i = 0; i < J; ++i) {
        for (int k = 0; k < M; ++k) {
            perm.push_back(i);
        }
    }

    // Random number generator setup
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    // Generate a good initial solution by trying a few random shuffles
    shuffle(perm.begin(), perm.end(), rng);
    long long best_makespan = get_makespan(perm);
    vector<int> best_perm = perm;

    for(int i=0; i<100; ++i) {
        shuffle(perm.begin(), perm.end(), rng);
        long long score = get_makespan(perm);
        if(score < best_makespan) {
            best_makespan = score;
            best_perm = perm;
        }
    }

    // Prepare for Simulated Annealing
    vector<int> current_perm = best_perm;
    long long current_score = best_makespan;
    
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.95; // Time limit slightly under typical 2s to be safe

    // Estimate initial temperature based on average delta of random moves
    double sum_delta = 0;
    int count = 0;
    for(int i=0; i<200; ++i) {
        int u = uniform_int_distribution<int>(0, J*M - 1)(rng);
        int v = uniform_int_distribution<int>(0, J*M - 1)(rng);
        if(u == v) continue;
        
        swap(current_perm[u], current_perm[v]);
        long long sc = get_makespan(current_perm);
        long long diff = sc - current_score;
        if(diff > 0) {
            sum_delta += diff;
            count++;
        }
        // Swap back to revert
        swap(current_perm[u], current_perm[v]);
    }
    
    double initial_temp = 100.0; // Fallback
    if (count > 0) {
        double avg = sum_delta / count;
        // Set temp such that probability of accepting avg deterioration is 50%
        initial_temp = -avg / log(0.5); 
    }

    double temp = initial_temp;
    long long iter = 0;

    // Main SA Loop
    while(true) {
        // Update temperature and check time every 1024 iterations to reduce overhead
        if ((iter & 0x3FF) == 0) {
            auto now = chrono::steady_clock::now();
            chrono::duration<double> elapsed = now - start_time;
            if (elapsed.count() > time_limit) break;
            
            // Linear cooling schedule: temp goes to 0 at time_limit
            double progress = elapsed.count() / time_limit;
            temp = initial_temp * (1.0 - progress);
            if(temp < 1e-6) temp = 1e-6;
        }
        iter++;

        // Neighborhood move: Swap two random elements in the permutation
        int u = uniform_int_distribution<int>(0, J*M - 1)(rng);
        int v = uniform_int_distribution<int>(0, J*M - 1)(rng);
        if(u == v) continue;

        swap(current_perm[u], current_perm[v]);
        long long new_score = get_makespan(current_perm);

        bool accept = false;
        if (new_score <= current_score) {
            accept = true;
            if (new_score < best_makespan) {
                best_makespan = new_score;
                best_perm = current_perm;
            }
        } else {
            // Metropolis criterion
            double delta = (double)(new_score - current_score);
            if (uniform_real_distribution<double>(0, 1)(rng) < exp(-delta / temp)) {
                accept = true;
            }
        }

        if (accept) {
            current_score = new_score;
        } else {
            // Revert move
            swap(current_perm[u], current_perm[v]);
        }
    }

    // Output the best solution found
    print_solution(best_perm);

    return 0;
}