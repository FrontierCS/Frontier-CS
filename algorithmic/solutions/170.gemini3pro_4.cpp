#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>
#include <queue>

using namespace std;

// Constants
const int N = 100;
const int L = 500000;

// Global variables
int T[N];
int adj[N][2]; // 0: a_i, 1: b_i
int weights[N][2]; // weights[i][0] = ceil(T_i/2), weights[i][1] = floor(T_i/2)
int current_loads[N];
int target_loads[N];

// Random number generator
mt19937 rng(12345);

// Time keeping
auto start_time = chrono::high_resolution_clock::now();

double get_time() {
    auto now = chrono::high_resolution_clock::now();
    return chrono::duration<double>(now - start_time).count();
}

// Function to calculate score (error)
// Score = sum |current_load[i] - target_loads[i]|
long long calculate_error() {
    long long error = 0;
    for (int i = 0; i < N; ++i) {
        error += abs(current_loads[i] - target_loads[i]);
    }
    return error;
}

// Check connectivity: return true if all nodes with T[i] > 0 are reachable from 0
bool check_connectivity() {
    vector<bool> reached(N, false);
    queue<int> q;
    
    q.push(0);
    reached[0] = true;
    
    while(!q.empty()){
        int u = q.front();
        q.pop();
        
        // Add children
        int v1 = adj[u][0];
        if(!reached[v1]) {
            reached[v1] = true;
            q.push(v1);
        }
        int v2 = adj[u][1];
        if(!reached[v2]) {
            reached[v2] = true;
            q.push(v2);
        }
    }
    
    for(int i=0; i<N; ++i) {
        if(T[i] > 0 && !reached[i]) return false;
    }
    return true;
}

// Helper to get unreached nodes
vector<int> get_unreached() {
    vector<bool> reached(N, false);
    queue<int> q;
    q.push(0);
    reached[0] = true;
    while(!q.empty()){
        int u = q.front();
        q.pop();
        int v1 = adj[u][0];
        if(!reached[v1]) { reached[v1] = true; q.push(v1); }
        int v2 = adj[u][1];
        if(!reached[v2]) { reached[v2] = true; q.push(v2); }
    }
    vector<int> unreached;
    for(int i=0; i<N; ++i) {
        if(T[i] > 0 && !reached[i]) unreached.push_back(i);
    }
    return unreached;
}

// Helper to get reachable nodes
vector<int> get_reachable() {
    vector<bool> reached(N, false);
    queue<int> q;
    q.push(0);
    reached[0] = true;
    while(!q.empty()){
        int u = q.front();
        q.pop();
        int v1 = adj[u][0];
        if(!reached[v1]) { reached[v1] = true; q.push(v1); }
        int v2 = adj[u][1];
        if(!reached[v2]) { reached[v2] = true; q.push(v2); }
    }
    vector<int> res;
    for(int i=0; i<N; ++i) if(reached[i]) res.push_back(i);
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int n_in, l_in;
    if (!(cin >> n_in >> l_in)) return 0;
    
    for (int i = 0; i < N; ++i) {
        cin >> T[i];
    }
    
    // Prepare weights and targets
    for (int i = 0; i < N; ++i) {
        weights[i][0] = (T[i] + 1) / 2; // Ceil
        weights[i][1] = T[i] / 2;       // Floor
        
        target_loads[i] = T[i];
    }
    // Adjust target for node 0 (since it receives flow from "start" which is not an edge)
    // The sum of incoming edge flows to 0 should be T[0] - 1.
    target_loads[0] -= 1; 
    
    // Initial random assignment
    for (int i = 0; i < N; ++i) {
        adj[i][0] = rng() % N;
        adj[i][1] = rng() % N;
    }
    
    // Calculate initial loads
    fill(current_loads, current_loads + N, 0);
    for (int i = 0; i < N; ++i) {
        current_loads[adj[i][0]] += weights[i][0];
        current_loads[adj[i][1]] += weights[i][1];
    }
    
    long long current_score = calculate_error();
    
    // Phase 1: SA for Flow Balance (ignoring connectivity)
    // Run for 1.2 seconds approx
    double limit_time_1 = 1.2;
    double t0 = 1000.0;
    
    int iter = 0;
    while (true) {
        iter++;
        if ((iter & 255) == 0) {
            double curr_time = get_time();
            if (curr_time > limit_time_1) break;
        }
        
        // Propose move
        int u = rng() % N;
        int slot = rng() % 2; // 0 or 1
        int old_v = adj[u][slot];
        int new_v = rng() % N;
        
        if (old_v == new_v) continue;
        
        int w = weights[u][slot];
        
        // Calculate score change
        // Only load of old_v and new_v change
        long long old_partial = abs(current_loads[old_v] - target_loads[old_v]) + 
                                abs(current_loads[new_v] - target_loads[new_v]);
        
        // Tentative update
        int l_old = current_loads[old_v] - w;
        int l_new = current_loads[new_v] + w;
        
        long long new_partial = abs(l_old - target_loads[old_v]) + 
                                abs(l_new - target_loads[new_v]);
        
        long long diff = new_partial - old_partial;
        
        // Acceptance
        double temp = t0 * (1.0 - get_time() / limit_time_1);
        if (temp < 0) temp = 0;
        
        bool accept = false;
        if (diff < 0) accept = true;
        else if (diff == 0) accept = true; 
        else {
             if (temp > 0 && exp(-diff * 100.0 / temp) * 1000 > (rng() % 1000)) accept = true; 
        }
        
        if (accept) {
            current_loads[old_v] = l_old;
            current_loads[new_v] = l_new;
            current_score += diff;
            adj[u][slot] = new_v;
        }
    }
    
    // Phase 2: Fix Connectivity
    while (true) {
        vector<int> unreached = get_unreached();
        if (unreached.empty()) break;
        
        // We need to connect reachable set R to unreached set U
        vector<int> R = get_reachable();
        
        int best_u = -1;
        int best_slot = -1;
        int best_v = -1;
        long long best_diff = 1e18;
        
        // Try to connect some u in R to some v in unreached
        // We iterate all R, and check both slots. Target any v in unreached.
        // To save time, we can try all v in unreached, or just pick one.
        // Connecting to any v in unreached component makes the whole component reachable (eventually).
        // Let's try all v in unreached to find the minimal cost impact.
        
        for (int u : R) {
            for (int slot = 0; slot < 2; ++slot) {
                int old_v = adj[u][slot];
                int w = weights[u][slot];
                
                for (int v : unreached) {
                     if (v == old_v) continue;
                     
                     long long old_partial = abs(current_loads[old_v] - target_loads[old_v]) + 
                                             abs(current_loads[v] - target_loads[v]);
                     
                     int l_old = current_loads[old_v] - w;
                     int l_v = current_loads[v] + w;
                     
                     long long new_partial = abs(l_old - target_loads[old_v]) + 
                                             abs(l_v - target_loads[v]);
                     
                     long long diff = new_partial - old_partial;
                     
                     if (diff < best_diff) {
                         best_diff = diff;
                         best_u = u;
                         best_slot = slot;
                         best_v = v;
                     }
                }
            }
        }
        
        if (best_u != -1) {
            int old_v = adj[best_u][best_slot];
            int w = weights[best_u][best_slot];
            current_loads[old_v] -= w;
            current_loads[best_v] += w;
            adj[best_u][best_slot] = best_v;
            current_score += best_diff;
        } else {
            // Should not be reachable here
            break; 
        }
    }
    
    // Phase 3: Optimize with connectivity constraints
    double limit_time_2 = 1.95;
    
    while (true) {
        iter++;
        if ((iter & 255) == 0) {
            if (get_time() > limit_time_2) break;
        }
        
        int u = rng() % N;
        int slot = rng() % 2;
        int old_v = adj[u][slot];
        int new_v = rng() % N;
        
        if (old_v == new_v) continue;
        
        int w = weights[u][slot];
        
        long long old_partial = abs(current_loads[old_v] - target_loads[old_v]) + 
                                abs(current_loads[new_v] - target_loads[new_v]);
        
        int l_old = current_loads[old_v] - w;
        int l_new = current_loads[new_v] + w;
        
        long long new_partial = abs(l_old - target_loads[old_v]) + 
                                abs(l_new - target_loads[new_v]);
                                
        long long diff = new_partial - old_partial;
        
        bool potential_accept = false;
        if (diff < 0) potential_accept = true;
        else if (diff == 0 && (rng()%10 == 0)) potential_accept = true; 
        else if (diff > 0 && (rng()%1000 == 0)) potential_accept = true;
        
        if (potential_accept) {
            // Tentatively apply and check connectivity
            adj[u][slot] = new_v;
            current_loads[old_v] = l_old;
            current_loads[new_v] = l_new;
            
            if (check_connectivity()) {
                // Keep
                current_score += diff;
            } else {
                // Revert
                adj[u][slot] = old_v;
                current_loads[old_v] += w; // restore
                current_loads[new_v] -= w; // restore
            }
        }
    }
    
    // Output
    for (int i = 0; i < N; ++i) {
        cout << adj[i][0] << " " << adj[i][1] << "\n";
    }
    
    return 0;
}