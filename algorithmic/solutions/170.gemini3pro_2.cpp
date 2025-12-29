#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <cmath>

using namespace std;

// Global variables
int N;
int L;
vector<int> T;
vector<long long> target_load;
vector<long long> current_load;

struct Item {
    int u;         // Source node
    int type;      // 0 for a_u, 1 for b_u
    int weight;    // Number of transitions provided by this edge
    int assigned_to; // Target node index
};

vector<Item> items;
vector<int> a, b;

// RNG
uint64_t rng_state = 123456789;
inline uint64_t xorshift() {
    uint64_t x = rng_state;
    x ^= x << 13;
    x ^= x >> 7;
    x ^= x << 17;
    return rng_state = x;
}
inline int rand_int(int n) {
    return xorshift() % n;
}

// Connectivity Check
// Returns sum of T[i] for all unreachable nodes i with T[i] > 0
// BFS from node 0
long long check_connectivity(const vector<int>& a_vec, const vector<int>& b_vec) {
    static vector<bool> visited;
    static vector<int> q;
    
    if (visited.size() != N) {
        visited.resize(N);
        q.reserve(N);
    }
    
    // Reset visited
    fill(visited.begin(), visited.end(), false);
    q.clear();
    
    q.push_back(0);
    visited[0] = true;
    
    int head = 0;
    while(head < (int)q.size()){
        int u = q[head++];
        
        // If T[u] >= 1, the edge u -> a[u] is traversed
        if (T[u] >= 1) {
            int v = a_vec[u];
            if (!visited[v]) {
                visited[v] = true;
                q.push_back(v);
            }
        }
        // If T[u] >= 2, the edge u -> b[u] is traversed
        if (T[u] >= 2) {
            int v = b_vec[u];
            if (!visited[v]) {
                visited[v] = true;
                q.push_back(v);
            }
        }
    }
    
    long long penalty = 0;
    for(int i=0; i<N; ++i){
        if(!visited[i] && T[i] > 0){
            penalty += T[i];
        }
    }
    return penalty;
}

// Calculate L1 error of load
long long calc_load_error() {
    long long err = 0;
    for(int i=0; i<N; ++i){
        err += abs(current_load[i] - target_load[i]);
    }
    return err;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    auto start_time = chrono::steady_clock::now();
    
    if (!(cin >> N >> L)) return 0;
    
    T.resize(N);
    target_load.resize(N);
    for(int i=0; i<N; ++i){
        cin >> T[i];
        target_load[i] = T[i];
    }
    
    // Adjust target for node 0
    // Node 0 receives the initial "start" token.
    // Flow balance: In + Start = Out + End
    // We target Out = T[i]. Thus In = T[i] - IsStart.
    target_load[0] -= 1;
    
    a.assign(N, 0);
    b.assign(N, 0);
    
    // Create items
    // Item A_i corresponds to edge u->a[u], used approx ceil(T[i]/2) times
    // Item B_i corresponds to edge u->b[u], used approx floor(T[i]/2) times
    items.reserve(2 * N);
    for(int i=0; i<N; ++i){
        if (T[i] >= 1) {
            int w = (T[i] + 1) / 2; // ceil(T[i]/2)
            items.push_back({i, 0, w, 0});
        }
        if (T[i] >= 2) {
            int w = T[i] / 2; // floor(T[i]/2)
            items.push_back({i, 1, w, 0});
        }
    }
    
    // Sort items by weight descending for greedy init
    sort(items.begin(), items.end(), [](const Item& x, const Item& y){
        return x.weight > y.weight;
    });
    
    // Greedy Initialization: Assign to bin with max deficit
    current_load.assign(N, 0);
    for(auto& it : items){
        int best_bin = 0;
        long long max_val = -2000000000000000000LL; // -infinity
        
        // Find bin that maximizes (Target - Current)
        for(int j=0; j<N; ++j){
            long long val = target_load[j] - current_load[j];
            if(val > max_val){
                max_val = val;
                best_bin = j;
            }
        }
        
        it.assigned_to = best_bin;
        current_load[best_bin] += it.weight;
        
        if(it.type == 0) a[it.u] = best_bin;
        else b[it.u] = best_bin;
    }
    
    // Initial cost evaluation
    long long curr_flow_err = calc_load_error();
    long long curr_conn_err = check_connectivity(a, b);
    double curr_cost = curr_flow_err + 1000.0 * curr_conn_err;
    
    double time_limit = 1.85; // seconds
    long long iter = 0;
    
    // Optimization Loop
    while(true){
        iter++;
        if((iter & 511) == 0){
            auto now = chrono::steady_clock::now();
            if(chrono::duration<double>(now - start_time).count() > time_limit) break;
        }
        
        // Neighbor: Move an item to a different bin
        int idx = rand_int((int)items.size());
        Item& it = items[idx];
        
        int old_bin = it.assigned_to;
        int new_bin;
        
        // Strategy: 40% Random, 60% Greedy-ish (Tournament)
        if(rand_int(100) < 40){
            new_bin = rand_int(N);
        } else {
            // Tournament selection: pick two random bins, choose the one with larger deficit
            int c1 = rand_int(N);
            int c2 = rand_int(N);
            long long d1 = target_load[c1] - current_load[c1];
            long long d2 = target_load[c2] - current_load[c2];
            new_bin = (d1 > d2) ? c1 : c2;
        }
        
        if(new_bin == old_bin) continue;
        
        // Apply change temporarily
        it.assigned_to = new_bin;
        current_load[old_bin] -= it.weight;
        current_load[new_bin] += it.weight;
        if(it.type == 0) a[it.u] = new_bin;
        else b[it.u] = new_bin;
        
        long long next_flow_err = calc_load_error();
        long long next_conn_err = check_connectivity(a, b);
        double next_cost = next_flow_err + 1000.0 * next_conn_err;
        
        // Acceptance criteria: Hill Climbing (Greedy Descent)
        // Since we have many iterations and side steps are allowed (<=), this works well.
        if(next_cost <= curr_cost){
            curr_cost = next_cost;
            curr_flow_err = next_flow_err;
            curr_conn_err = next_conn_err;
        } else {
            // Revert changes
            it.assigned_to = old_bin;
            current_load[old_bin] += it.weight;
            current_load[new_bin] -= it.weight;
            if(it.type == 0) a[it.u] = old_bin;
            else b[it.u] = old_bin;
        }
    }
    
    // Output result
    for(int i=0; i<N; ++i){
        cout << a[i] << " " << b[i] << "\n";
    }
    
    return 0;
}