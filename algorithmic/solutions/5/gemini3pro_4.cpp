#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <ctime>

using namespace std;

// Global constants and arrays to store graph and state
const int MAXN = 500005;

vector<int> adj[MAXN];
int in_degree[MAXN];
int current_in_degree[MAXN];
int out_degree[MAXN];
bool visited[MAXN];

// Random number generator
mt19937 rng(1337); 

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    
    // Consume scoring parameters
    int temp;
    for(int i=0; i<10; ++i) cin >> temp;
    
    for(int i=0; i<m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        out_degree[u]++;
        in_degree[v]++;
    }
    
    // Identify potential start nodes (nodes with in-degree 0)
    vector<int> start_candidates;
    for(int i=1; i<=n; ++i) {
        if(in_degree[i] == 0) {
            start_candidates.push_back(i);
        }
    }
    
    vector<int> best_path;
    int max_len = 0;
    
    clock_t start_time = clock();
    double time_limit = 3.85; // Time limit safe margin (Total limit 4s)
    
    while (true) {
        // Check time limit
        if ((double)(clock() - start_time) / CLOCKS_PER_SEC > time_limit) break;
        
        // Restore state for the new run
        for(int i=1; i<=n; ++i) {
            current_in_degree[i] = in_degree[i];
            visited[i] = false;
        }
        
        // Select start node
        int curr;
        if (!start_candidates.empty()) {
            // If there are nodes with in-degree 0, the path must start at one of them
            uniform_int_distribution<int> dist(0, start_candidates.size() - 1);
            curr = start_candidates[dist(rng)];
        } else {
            // If no in-degree 0 nodes, pick random node
            uniform_int_distribution<int> dist(1, n);
            curr = dist(rng);
        }
        
        vector<int> current_path;
        current_path.reserve(n);
        
        visited[curr] = true;
        current_path.push_back(curr);
        
        // Update degrees for the start node
        for(int v : adj[curr]) {
            current_in_degree[v]--;
        }
        
        // Greedy DFS traversal
        while((int)current_path.size() < n) {
            // Heuristic:
            // 1. Pick neighbor with lowest current_in_degree (most constrained)
            // 2. Tie-breaker: Pick neighbor with highest out_degree (most options forward)
            // 3. Tie-breaker: Random
            
            int min_deg = 1e9;
            vector<int> candidates;
            
            for(int v : adj[curr]) {
                if(!visited[v]) {
                    if(current_in_degree[v] < min_deg) {
                        min_deg = current_in_degree[v];
                        candidates.clear();
                        candidates.push_back(v);
                    } else if(current_in_degree[v] == min_deg) {
                        candidates.push_back(v);
                    }
                }
            }
            
            if(candidates.empty()) break; // Stuck
            
            int next_node = -1;
            
            if(candidates.size() == 1) {
                next_node = candidates[0];
            } else {
                // Secondary filter: max out_degree
                int max_out = -1;
                vector<int> best_candidates;
                for(int v : candidates) {
                    if(out_degree[v] > max_out) {
                        max_out = out_degree[v];
                        best_candidates.clear();
                        best_candidates.push_back(v);
                    } else if(out_degree[v] == max_out) {
                        best_candidates.push_back(v);
                    }
                }
                
                if(best_candidates.size() == 1) {
                    next_node = best_candidates[0];
                } else {
                    uniform_int_distribution<int> dist(0, best_candidates.size() - 1);
                    next_node = best_candidates[dist(rng)];
                }
            }
            
            curr = next_node;
            visited[curr] = true;
            current_path.push_back(curr);
            
            // Update degrees for the chosen node
            for(int v : adj[curr]) {
                if(!visited[v]) {
                    current_in_degree[v]--;
                }
            }
        }
        
        if((int)current_path.size() > max_len) {
            max_len = current_path.size();
            best_path = current_path;
        }
        
        if(max_len == n) break; // Found a Hamiltonian Path
    }
    
    cout << best_path.size() << "\n";
    for(int i=0; i<(int)best_path.size(); ++i) {
        cout << best_path[i] << (i == (int)best_path.size()-1 ? "" : " ");
    }
    cout << "\n";
    
    return 0;
}