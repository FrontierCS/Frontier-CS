#include <iostream>
#include <vector>
#include <bitset>
#include <algorithm>
#include <ctime>
#include <numeric>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 1005;
using BitSet = bitset<MAXN>;

// Global Variables
int N, M;
BitSet adj[MAXN]; // Adjacency matrix of the COMPLEMENT graph
// adj[i][j] = 1 means vertices i and j can both be in Independent Set (i.e. no edge in original graph)

vector<int> current_sol;
vector<int> best_sol;
int best_size = 0;

double start_time;
long long ops_counter = 0;

// Mapping for vertex reordering (heuristic optimization)
int old_to_new[MAXN];
int new_to_old[MAXN];
int deg_in_g[MAXN]; 

// Check for time limit (limit slightly below 2.0s to be safe)
bool time_limit_exceeded() {
    return (double)(clock() - start_time) / CLOCKS_PER_SEC > 1.95;
}

struct VertexInfo {
    int id;
    int color;
};

// Computes coloring upper-bound for a set of vertices
// Sorts/returns vertices paired with their chromatic limit
void color_sort(const BitSet& P, vector<VertexInfo>& listing) {
    if (P.none()) {
        listing.clear();
        return;
    }

    // Extract vertices from bitset
    vector<int> nodes;
    nodes.reserve(P.count());
    for (int i = 1; i <= N; ++i) { 
        if (P[i]) nodes.push_back(i);
    }

    vector<int> node_colors(nodes.size()); 
    // `used` tracks forbidden colors for the current vertex being colored
    vector<int> used(nodes.size() + 2, 0); 
    
    // Greedy coloring from back to front (based on index in `nodes`)
    // `nodes` are sorted by new index 1..N, so degree-based roughly
    // We compute color `k` for `nodes[i]` considering neighbors in `nodes[i+1...end]`
    // This `k` serves as an upper bound for max clique size in suffix.
    for (int i = (int)nodes.size() - 1; i >= 0; --i) {
        int u = nodes[i];
        int k = 1;
        
        // Check neighbors appearing later in the list
        for (size_t j = i + 1; j < nodes.size(); ++j) {
            int v = nodes[j];
            if (adj[u][v]) {
                used[node_colors[j]] = i + 1; // Mark color as used (versioned by i+1)
            }
        }
        // Find smallest unused color
        while (used[k] == i + 1) k++;
        node_colors[i] = k;
    }
    
    listing.resize(nodes.size());
    for(size_t i=0; i<nodes.size(); ++i) {
        listing[i] = {nodes[i], node_colors[i]};
    }
}

// Recursive Maximum Clique search on Complement Graph
void expand(BitSet candidates) {
    // Check time limit periodically
    if ((++ops_counter & 2047) == 0 && time_limit_exceeded()) return;
    
    if (candidates.none()) {
        if ((int)current_sol.size() > best_size) {
            best_size = (int)current_sol.size();
            best_sol = current_sol;
        }
        return;
    }
    
    // Basic Pruning
    if ((int)current_sol.size() + (int)candidates.count() <= best_size) return;

    vector<VertexInfo> sorted_candidates;
    color_sort(candidates, sorted_candidates);
    
    for (size_t i = 0; i < sorted_candidates.size(); ++i) {
        if ((ops_counter & 2047) == 0 && time_limit_exceeded()) return;
        
        // Coloring Bound Pruning
        // sorted_candidates[i].color is an upper bound on the clique size formed by 
        // the current candidate and valid subsequent candidates.
        if ((int)current_sol.size() + sorted_candidates[i].color <= best_size) {
            return;
        }
        
        int u = sorted_candidates[i].id;
        
        current_sol.push_back(u);
        
        // Construct new candidates set:
        // Must be in `candidates` AND neighbors of `u` (in complement)
        // AND must appear after `u` in the sorted list to avoid duplicates/visited.
        BitSet new_candidates;
        for (size_t j = i + 1; j < sorted_candidates.size(); ++j) {
            int v = sorted_candidates[j].id;
            if (adj[u][v]) {
                new_candidates.set(v);
            }
        }
        
        expand(new_candidates);
        current_sol.pop_back();
    }
}

// Initial Fast Greedy Heuristic to establish a good lower bound
void greedy_heuristic() {
    BitSet remaining;
    for(int i=1; i<=N; ++i) remaining.set(i);
            
    vector<int> sol;
    
    while (remaining.count() > 0) {
        int best_v = -1;
        int max_deg = -1;
        
        // Select vertex with max degree in the remaining induced subgraph (Complement)
        // 1-based loop, 1 is usually high degree due to sorting
        for (int v = 1; v <= N; ++v) {
            if (remaining[v]) {
                int d = (int)(remaining & adj[v]).count();
                if (d > max_deg) {
                    max_deg = d;
                    best_v = v;
                }
            }
        }
        
        if (best_v == -1) break;
        
        sol.push_back(best_v);
        // Keep only neighbors in complement (compatible vertices)
        remaining &= adj[best_v]; 
    }
    
    if ((int)sol.size() > best_size) {
        best_size = (int)sol.size();
        best_sol = sol;
    }
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    start_time = clock();
    
    if (!(cin >> N >> M)) return 0;
    
    vector<pair<int, int>> edges;
    edges.reserve(M);
    
    // Read edges and compute degrees
    fill(deg_in_g, deg_in_g + N + 1, 0);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        edges.push_back({u, v});
        deg_in_g[u]++;
        deg_in_g[v]++;
    }
    
    // Sort vertices map such that index 1 corresponds to vertex with Minimum Degree in G (Max Degree in Complement)
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);
    sort(p.begin(), p.end(), [&](int a, int b) {
        if (deg_in_g[a] != deg_in_g[b])
            return deg_in_g[a] < deg_in_g[b];
        return a < b; 
    });
    
    for (int i = 0; i < N; ++i) {
        old_to_new[p[i]] = i + 1;
        new_to_old[i + 1] = p[i];
    }
    
    // Initialize Complement Adjacency Matrix
    for (int i = 1; i <= N; ++i) {
        adj[i].set(); // Set all bits to 1
        adj[i][i] = 0;
        adj[i][0] = 0; // 0 index unused
        for(int k=N+1; k<MAXN; ++k) adj[i][k] = 0; // Out of bounds 0
    }
    
    // Updates according to input edges
    for (auto& e : edges) {
        int u = old_to_new[e.first];
        int v = old_to_new[e.second];
        // If edge exists in Original, it does NOT exist in Complement
        adj[u][v] = 0;
        adj[v][u] = 0;
    }
    
    // Step 1: Greedy Heuristic
    greedy_heuristic();
    
    // Step 2: Branch and Bound Search
    BitSet candidates;
    for(int i=1; i<=N; ++i) candidates.set(i);
    expand(candidates);
    
    // Output Result
    vector<int> result(N + 1, 0);
    for (int u : best_sol) {
        result[new_to_old[u]] = 1;
    }
    
    for (int i = 1; i <= N; ++i) {
        cout << result[i] << "\n";
    }
    
    return 0;
}