#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 500005;

// Graph and degree information
vector<int> adj[MAXN];
int in_degree[MAXN];
int out_degree[MAXN];

// Visited array for DFS
bool visited[MAXN];
// To keep track of the current neighbor index for each node during iterative DFS
int cur_edge[MAXN]; 

// Path storage
vector<int> best_path;
vector<int> current_path;

int n, m;
vector<int> a(10); // Scoring parameters (unused in logic)

// Comparator to sort neighbors:
// 1. Prefer neighbors with lower in-degree (harder to reach later)
// 2. Prefer neighbors that are not dead ends (out-degree > 0)
// 3. Prefer neighbors with lower out-degree (Warnsdorff's heuristic)
bool compareNeighbors(int u, int v) {
    if (in_degree[u] != in_degree[v])
        return in_degree[u] < in_degree[v];
    
    bool term_u = (out_degree[u] == 0);
    bool term_v = (out_degree[v] == 0);
    if (term_u != term_v) return !term_u; // Non-terminal nodes come first
    
    return out_degree[u] < out_degree[v];
}

// Comparator for choosing start nodes
bool compareStartNodes(int u, int v) {
    if (in_degree[u] != in_degree[v])
        return in_degree[u] < in_degree[v];
    return out_degree[u] < out_degree[v];
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;
    
    for (int i = 0; i < 10; ++i) cin >> a[i];

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        out_degree[u]++;
        in_degree[v]++;
    }

    // Sort adjacency lists based on heuristic
    for (int i = 1; i <= n; ++i) {
        sort(adj[i].begin(), adj[i].end(), compareNeighbors);
    }

    // Identify potential start nodes
    vector<int> start_nodes;
    start_nodes.reserve(n);
    for (int i = 1; i <= n; ++i) {
        start_nodes.push_back(i);
    }
    
    sort(start_nodes.begin(), start_nodes.end(), compareStartNodes);

    // Heuristic: if nodes with in-degree 0 exist, start must be one of them.
    // Otherwise, try a few best candidates.
    int candidates_to_try = min(n, 20); 
    int zero_in_count = 0;
    for(int u : start_nodes) if(in_degree[u] == 0) zero_in_count++;
    if(zero_in_count > 0) candidates_to_try = zero_in_count; 

    // Time management
    clock_t start_time = clock();
    double time_limit = 3.8; 
    long long operations = 0;
    
    for (int k = 0; k < candidates_to_try; ++k) {
        int start_node = start_nodes[k];
        
        current_path.clear();
        current_path.reserve(n);
        
        // Initialize DFS from start_node
        current_path.push_back(start_node);
        visited[start_node] = true;
        cur_edge[start_node] = 0;
        
        if (current_path.size() > best_path.size()) {
            best_path = current_path;
        }

        // Iterative DFS
        while (!current_path.empty()) {
            operations++;
            // Check time limit periodically
            if ((operations & 65535) == 0) {
                if ((double)(clock() - start_time) / CLOCKS_PER_SEC > time_limit) goto end_search;
            }

            int u = current_path.back();
            
            // If Hamiltonian path found
            if (current_path.size() == n) {
                best_path = current_path;
                goto end_search; 
            }
            
            bool found = false;
            // Try to find an unvisited neighbor
            while (cur_edge[u] < adj[u].size()) {
                int v = adj[u][cur_edge[u]];
                cur_edge[u]++;
                if (!visited[v]) {
                    visited[v] = true;
                    current_path.push_back(v);
                    cur_edge[v] = 0; // Reset iterator for the new node
                    found = true;
                    if (current_path.size() > best_path.size()) {
                        best_path = current_path;
                    }
                    break; // Successfully pushed a neighbor
                }
            }

            if (!found) {
                // Backtrack
                visited[u] = false;
                cur_edge[u] = 0; // Reset iterator for future visits
                current_path.pop_back();
            }
        }
    }

end_search:
    cout << best_path.size() << "\n";
    for (int i = 0; i < best_path.size(); ++i) {
        cout << best_path[i] << (i == best_path.size() - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}