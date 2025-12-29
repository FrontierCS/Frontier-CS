#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Structure to represent an outgoing edge option
struct Item {
    int id;          // unique id of the item
    int weight;      // flow weight of this edge
    int from_node;   // origin node
    int type;        // 0 for a_i, 1 for b_i
};

int N;
int L;
vector<int> T;
vector<Item> items;
vector<int> R; // Target inflow for each node

// State
vector<int> assignment; // item_id -> destination bin_id
vector<int> current_loads; // bin_id -> current inflow

// Random number generator
mt19937 rng(12345);

// Check reachability from node 0 considering only edges that are effectively used
int check_connectivity(const vector<int>& assign) {
    // Adjacency list with static arrays for performance
    static int adj[100][2];
    static int deg[100];
    for(int i=0; i<N; ++i) deg[i] = 0;
    
    // Fill adjacency list
    // An edge 'a_i' exists if we visit i at least once (T[i] >= 1) or if i is start node (0)
    // An edge 'b_i' exists if we visit i at least twice (T[i] >= 2)
    for(int i=0; i<N; ++i) {
        bool has_a = (T[i] >= 1 || i == 0);
        bool has_b = (T[i] >= 2);
        if(has_a) {
            adj[i][deg[i]++] = assign[2*i];
        }
        if(has_b) {
            adj[i][deg[i]++] = assign[2*i + 1];
        }
    }
    
    // BFS from node 0
    static bool visited[100];
    for(int i=0; i<N; ++i) visited[i] = false;
    static int q[105];
    int q_head = 0, q_tail = 0;
    
    visited[0] = true;
    q[q_tail++] = 0;
    
    while(q_head < q_tail) {
        int u = q[q_head++];
        for(int k=0; k<deg[u]; ++k) {
            int v = adj[u][k];
            if(!visited[v]) {
                visited[v] = true;
                q[q_tail++] = v;
            }
        }
    }
    
    // Count how many nodes with target > 0 are reached
    int reachable_target_count = 0;
    for(int i=0; i<N; ++i) {
        if(T[i] > 0 && visited[i]) {
            reachable_target_count++;
        }
    }
    return reachable_target_count;
}

// Score calculation: Flow Error + Connectivity Penalty
long long calc_score(const vector<int>& loads, int reachable_cnt, int total_target_nodes) {
    long long flow_err = 0;
    for(int i=0; i<N; ++i) {
        flow_err += abs((long long)loads[i] - (long long)R[i]);
    }
    long long penalty = 0;
    if(reachable_cnt < total_target_nodes) {
        // Large penalty to enforce connectivity
        penalty = 100000000LL; 
        penalty += (long long)(total_target_nodes - reachable_cnt) * 1000000LL;
    }
    return flow_err + penalty;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> L)) return 0;
    T.resize(N);
    int total_target_nodes = 0;
    for(int i=0; i<N; ++i) {
        cin >> T[i];
        if(T[i] > 0) total_target_nodes++;
    }

    R.resize(N);
    for(int i=0; i<N; ++i) {
        R[i] = T[i];
    }
    // Node 0 receives one unit of flow from 'outside' (start of process), so its requirement from network is T[0] - 1.
    // However, if T[0]=0, R[0] = -1. But load >= 0, so min error is 1. This is correct as we are forced to visit 0 once.
    R[0]--; 

    items.clear();
    for(int i=0; i<N; ++i) {
        // a_i is taken on 1st, 3rd... visits
        int w_a = (T[i] + 1) / 2;
        items.push_back({2*i, w_a, i, 0});
        // b_i is taken on 2nd, 4th... visits
        int w_b = T[i] / 2;
        items.push_back({2*i + 1, w_b, i, 1});
    }

    // Initial Greedy Assignment
    // Sort items by weight descending to solve bin packing greedily
    vector<int> p(2*N);
    iota(p.begin(), p.end(), 0);
    sort(p.begin(), p.end(), [&](int i, int j){
        return items[i].weight > items[j].weight;
    });

    assignment.assign(2*N, 0);
    current_loads.assign(N, 0);

    for(int idx : p) {
        int best_bin = 0;
        long long max_def = -1e18; // Deficit = Target - Current Load
        
        // Find bin with largest deficit
        // Use reservoir sampling for tie-breaking
        int count = 0;
        for(int j=0; j<N; ++j) {
            long long def = (long long)R[j] - current_loads[j];
            if(def > max_def) {
                max_def = def;
                best_bin = j;
                count = 1;
            } else if(def == max_def) {
                count++;
                if(uniform_int_distribution<int>(0, count-1)(rng) == 0) {
                    best_bin = j;
                }
            }
        }
        assignment[items[idx].id] = best_bin;
        current_loads[best_bin] += items[idx].weight;
    }

    // Simulated Annealing
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.95;

    int current_reachable = check_connectivity(assignment);
    long long current_score = calc_score(current_loads, current_reachable, total_target_nodes);
    
    double start_temp = 2000.0;
    double end_temp = 0.1;
    double temp = start_temp;
    
    int iter = 0;
    
    while(true) {
        iter++;
        // Check time periodically
        if((iter & 511) == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if(elapsed > time_limit) break;
            double ratio = elapsed / time_limit;
            temp = start_temp * pow(end_temp / start_temp, ratio);
        }

        // Propose a move: Reassign or Swap
        int move_type = rng() % 2; 
        
        if(move_type == 0) { // Reassign one item to a different bin
            int item_idx = rng() % (2*N);
            int old_bin = assignment[item_idx];
            int new_bin = rng() % N;
            if(old_bin == new_bin) continue;
            
            // Calculate new score
            long long old_load_err = abs((long long)current_loads[old_bin] - R[old_bin]) + abs((long long)current_loads[new_bin] - R[new_bin]);
            
            assignment[item_idx] = new_bin;
            current_loads[old_bin] -= items[item_idx].weight;
            current_loads[new_bin] += items[item_idx].weight;
            
            long long new_load_err = abs((long long)current_loads[old_bin] - R[old_bin]) + abs((long long)current_loads[new_bin] - R[new_bin]);
            
            // Re-check connectivity
            int new_reachable = check_connectivity(assignment);
            long long new_total_score = calc_score(current_loads, new_reachable, total_target_nodes);
            
            long long delta = new_total_score - current_score;
            
            if(delta <= 0 || bernoulli_distribution(exp(-delta / temp))(rng)) {
                current_score = new_total_score;
                current_reachable = new_reachable;
            } else {
                // Revert
                assignment[item_idx] = old_bin;
                current_loads[old_bin] += items[item_idx].weight;
                current_loads[new_bin] -= items[item_idx].weight;
            }
        } else { // Swap the bins of two items
            int i1 = rng() % (2*N);
            int i2 = rng() % (2*N);
            if(i1 == i2) continue;
            int b1 = assignment[i1];
            int b2 = assignment[i2];
            if(b1 == b2) continue;
            
            long long old_load_err = abs((long long)current_loads[b1] - R[b1]) + abs((long long)current_loads[b2] - R[b2]);
            
            // Apply swap
            assignment[i1] = b2;
            assignment[i2] = b1;
            
            current_loads[b1] = current_loads[b1] - items[i1].weight + items[i2].weight;
            current_loads[b2] = current_loads[b2] - items[i2].weight + items[i1].weight;
            
            long long new_load_err = abs((long long)current_loads[b1] - R[b1]) + abs((long long)current_loads[b2] - R[b2]);
            
            int new_reachable = check_connectivity(assignment);
            long long new_total_score = calc_score(current_loads, new_reachable, total_target_nodes);
            
            long long delta = new_total_score - current_score;
            
            if(delta <= 0 || bernoulli_distribution(exp(-delta / temp))(rng)) {
                current_score = new_total_score;
                current_reachable = new_reachable;
            } else {
                // Revert
                assignment[i1] = b1;
                assignment[i2] = b2;
                current_loads[b1] = current_loads[b1] - items[i2].weight + items[i1].weight;
                current_loads[b2] = current_loads[b2] - items[i1].weight + items[i2].weight;
            }
        }
    }

    // Output
    for(int i=0; i<N; ++i) {
        cout << assignment[2*i] << " " << assignment[2*i+1] << "\n";
    }

    return 0;
}