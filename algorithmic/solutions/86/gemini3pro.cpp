#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <cstdlib>

using namespace std;

// Global variables
int n;
vector<vector<int>> adj; // Adjacency list for the constructed tree
// We don't maintain global subtree sizes, we compute locally.

// Query function
int query(int u, int v, int w) {
    cout << "0 " << u << " " << v << " " << w << endl;
    int res;
    cin >> res;
    return res;
}

// Function to find the edge (u, v) and split it with mid
void split_edge(int u, int v, int mid) {
    for (size_t i = 0; i < adj[u].size(); ++i) {
        if (adj[u][i] == v) {
            adj[u].erase(adj[u].begin() + i);
            break;
        }
    }
    for (size_t i = 0; i < adj[v].size(); ++i) {
        if (adj[v][i] == u) {
            adj[v].erase(adj[v].begin() + i);
            break;
        }
    }
    adj[u].push_back(mid);
    adj[mid].push_back(u);
    adj[mid].push_back(v);
    adj[v].push_back(mid);
}

// Function to add a new node u to the tree
void insert_node(int u) {
    int curr = 1;
    int prev = -1;
    
    while (true) {
        // Collect active neighbors (excluding where we came from)
        vector<int> neighbors;
        for (int v : adj[curr]) {
            if (v != prev) {
                neighbors.push_back(v);
            }
        }
        
        if (neighbors.empty()) {
            adj[curr].push_back(u);
            adj[u].push_back(curr);
            return;
        }
        
        // Compute subtree sizes for sorting (HLD heuristic)
        vector<pair<int, int>> sorted_neighbors;
        static vector<int> visited_ver(n + 1, 0);
        static int version = 0;
        version++;
        visited_ver[curr] = version;
        
        for (int v : neighbors) {
            int count = 0;
            vector<int> q;
            q.push_back(v);
            visited_ver[v] = version;
            count = 1;
            size_t head = 0;
            while(head < q.size()){
                int node = q[head++];
                for(int neighbor : adj[node]) {
                    if(visited_ver[neighbor] != version) {
                        visited_ver[neighbor] = version;
                        q.push_back(neighbor);
                        count++;
                    }
                }
            }
            sorted_neighbors.push_back({count, v});
        }
        
        sort(sorted_neighbors.rbegin(), sorted_neighbors.rend());
        
        // Iterate through neighbors
        // We use pairing optimization for small children if the first (heavy) child fails
        
        // First, check the heavy child individually
        bool moved = false;
        
        // Indices to process
        size_t idx = 0;
        
        // Always check the heaviest child individually
        if (idx < sorted_neighbors.size()) {
            int v = sorted_neighbors[idx].second;
            idx++;
            
            int res = query(u, curr, v);
            if (res == v) {
                prev = curr;
                curr = v;
                moved = true;
            } else if (res == curr) {
                // eliminated v, continue to next
            } else {
                // split edge
                split_edge(curr, v, res);
                if (res != u) {
                    adj[res].push_back(u);
                    adj[u].push_back(res);
                }
                return;
            }
        }
        
        if (moved) continue;
        
        // Process remaining neighbors in pairs to save queries
        while (idx < sorted_neighbors.size()) {
            if (idx + 1 < sorted_neighbors.size()) {
                int v1 = sorted_neighbors[idx].second;
                int v2 = sorted_neighbors[idx+1].second;
                idx += 2;
                
                int res = query(u, v1, v2);
                if (res == curr) {
                    // u is in neither v1 nor v2 branch
                    continue;
                } else if (res == v1) {
                    prev = curr;
                    curr = v1;
                    moved = true;
                    break;
                } else if (res == v2) {
                    prev = curr;
                    curr = v2;
                    moved = true;
                    break;
                } else {
                    // res is a new node on path v1-curr-v2
                    // Determine which edge: (curr, v1) or (curr, v2)
                    // Query M(res, curr, v1)
                    int check = query(res, curr, v1);
                    if (check == res) {
                        // res is on (curr, v1)
                        split_edge(curr, v1, res);
                    } else {
                        // res is on (curr, v2)
                        split_edge(curr, v2, res);
                    }
                    if (res != u) {
                        adj[res].push_back(u);
                        adj[u].push_back(res);
                    }
                    return;
                }
            } else {
                // Single remaining neighbor
                int v = sorted_neighbors[idx].second;
                idx++;
                int res = query(u, curr, v);
                if (res == v) {
                    prev = curr;
                    curr = v;
                    moved = true;
                    break;
                } else if (res == curr) {
                    continue;
                } else {
                    split_edge(curr, v, res);
                    if (res != u) {
                        adj[res].push_back(u);
                        adj[u].push_back(res);
                    }
                    return;
                }
            }
        }
        
        if (!moved) {
            // Checked all neighbors, u is in none
            adj[curr].push_back(u);
            adj[u].push_back(curr);
            return;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> n)) return 0;
    
    adj.resize(n + 1);
    
    // Random insertion order
    vector<int> p(n - 1);
    iota(p.begin(), p.end(), 2);
    srand(12345); 
    random_shuffle(p.begin(), p.end());
    
    for (int u : p) {
        insert_node(u);
    }
    
    cout << "1";
    for (int u = 1; u <= n; ++u) {
        for (int v : adj[u]) {
            if (u < v) {
                cout << " " << u << " " << v;
            }
        }
    }
    cout << endl;
    
    return 0;
}