#pragma GCC optimize("O3")
#include <iostream>
#include <vector>
#include <algorithm>
#include <bitset>
#include <ctime>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 1005;

int N, M;
// Adjacency matrix using bitset for memory efficiency and speed
bitset<MAXN> adj[MAXN];
// Stores the best clique found so far
vector<int> best_clique;
int max_sz = 0;
// Timer to handle time limit
clock_t start_time;

struct Vertex {
    int id;
    int deg;
};

// Main recursive function to find maximum clique
// R: Current clique vertices
// P: Candidate vertices that can extend R
void expand(vector<int>& R, vector<int>& P) {
    // Update best solution found so far
    if ((int)R.size() > max_sz) {
        max_sz = R.size();
        best_clique = R;
    }
    
    if (P.empty()) return;
    
    // Pruning 1: Even if we add all candidates, we can't beat max_sz
    if ((int)R.size() + (int)P.size() <= max_sz) return;
    
    // Time limit check (approx 1.95s to be safe within 2.0s)
    if ((double)(clock() - start_time) / CLOCKS_PER_SEC > 1.95) return;
    
    // Graph Coloring Heuristic to tighten upper bound
    // We color the subgraph induced by P.
    // The number of colors used is an upper bound on the max clique size in P.
    vector<int> color(P.size());
    int k_max = 0; // Max color index used
    
    // Greedy coloring
    for (int i = 0; i < (int)P.size(); ++i) {
        int u = P[i];
        int c = 1;
        // Find the smallest color c not used by neighbors of u that are already colored.
        // In our loop, neighbors already colored appear at indices j < i.
        while (true) {
            bool conflict = false;
            for (int j = 0; j < i; ++j) {
                if (color[j] == c && adj[u][P[j]]) {
                    conflict = true;
                    break;
                }
            }
            if (!conflict) break;
            c++;
        }
        color[i] = c;
        if (c > k_max) k_max = c;
    }
    
    // Pruning 2: Coloring bound
    if ((int)R.size() + k_max <= max_sz) return;
    
    // Sort candidates by color descending to process vertices with potential for larger cliques first
    // This allows earlier pruning in the loop.
    vector<pair<int, int>> sorted_P;
    sorted_P.reserve(P.size());
    for(int i = 0; i < (int)P.size(); ++i) {
        sorted_P.push_back({color[i], P[i]});
    }
    
    sort(sorted_P.begin(), sorted_P.end(), greater<pair<int, int>>());
    
    // Iterate through candidates
    for (int i = 0; i < (int)sorted_P.size(); ++i) {
        int c = sorted_P[i].first;
        int v = sorted_P[i].second;
        
        // Pruning 3: Dynamic coloring bound
        // If current clique size + color of v <= max_sz, we can stop.
        // Because sorted_P is descending by color, all subsequent vertices have color <= c.
        if ((int)R.size() + c <= max_sz) {
            break;
        }
        
        // Form new candidate set: neighbors of v that appear LATER in sorted_P
        // This ensures we don't process permutations of the same clique.
        vector<int> next_P;
        next_P.reserve(sorted_P.size() - 1 - i);
        
        for (int j = i + 1; j < (int)sorted_P.size(); ++j) {
            int u = sorted_P[j].second;
            if (adj[v][u]) {
                next_P.push_back(u);
            }
        }
        
        R.push_back(v);
        expand(R, next_P);
        R.pop_back();
        
        // Frequent time check
        if ((double)(clock() - start_time) / CLOCKS_PER_SEC > 1.95) return;
    }
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M)) return 0;
    
    start_time = clock();
    
    vector<int> deg(N, 0);
    // Read edges
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v; // Convert 1-based to 0-based
        if (u == v) continue; // Ignore self-loops
        
        // Only add if not already present (handle multi-edges)
        if (!adj[u][v]) {
            adj[u][v] = 1;
            adj[v][u] = 1;
            deg[u]++;
            deg[v]++;
        }
    }
    
    // Initial candidates P, sorted by degree descending.
    // High degree vertices are more likely to be in large cliques.
    vector<int> P(N);
    vector<Vertex> nodes(N);
    for (int i = 0; i < N; ++i) {
        nodes[i] = {i, deg[i]};
    }
    
    sort(nodes.begin(), nodes.end(), [](const Vertex& a, const Vertex& b) {
        return a.deg > b.deg;
    });
    
    for (int i = 0; i < N; ++i) {
        P[i] = nodes[i].id;
    }
    
    vector<int> R;
    R.reserve(N);
    
    // Start search
    expand(R, P);
    
    // Prepare output
    vector<int> res(N, 0);
    for (int v : best_clique) {
        res[v] = 1;
    }
    
    for (int i = 0; i < N; ++i) {
        cout << res[i] << "\n";
    }
    
    return 0;
}