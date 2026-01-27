#pragma GCC optimize("O3,unroll-loops")
#pragma GCC target("avx2,bmi,bmi2,lzcnt,popcnt")

#include <iostream>
#include <vector>
#include <algorithm>
#include <bitset>
#include <ctime>
#include <numeric>

using namespace std;

// Maximum number of vertices as per constraints + buffer
const int MAXN = 1005;

// Bitset for adjacency matrix
using BitSet = bitset<MAXN>;

int N, M;
BitSet adj[MAXN];

// Timer and operation counter for time limit handling
clock_t start_time;
const double TIME_LIMIT = 1.95; // Seconds
int ops_counter = 0;

struct MaxCliqueSolver {
    vector<int> maxQ; // Stores the best clique found so far
    vector<int> Q;    // Current clique being built

    // Main execution function
    void run() {
        vector<int> P(N);
        // Initialize P with vertices 1 to N
        iota(P.begin(), P.end(), 1);
        
        // Initial sorting of vertices by degree descending
        // This acts as a simple heuristic to potentially find larger cliques earlier
        sort(P.begin(), P.end(), [](int a, int b){
            return adj[a].count() > adj[b].count();
        });

        expand(P);
    }

    // Recursive function with pruning based on coloring
    void expand(vector<int>& P) {
        // Check time limit periodically
        if (++ops_counter > 1000) {
            ops_counter = 0;
            if ((double)(clock() - start_time) / CLOCKS_PER_SEC > TIME_LIMIT) return;
        }

        if (P.empty()) {
            if (Q.size() > maxQ.size()) {
                maxQ = Q;
            }
            return;
        }

        // Structure to hold vertex and its assigned color
        struct NodeInfo {
            int u;
            int color;
        };
        
        int sz = P.size();
        vector<NodeInfo> colored_P(sz);
        
        // Greedy coloring on the current candidate set P
        // Iterate backwards to compute upper bounds for clique size
        for (int i = sz - 1; i >= 0; --i) {
             int u = P[i];
             int k = 1;
             // Find the smallest color not used by neighbors of u that are subsequent in P (j > i)
             while (true) {
                 bool conflict = false;
                 for (int j = i + 1; j < sz; ++j) {
                     if (colored_P[j].color == k && adj[u][colored_P[j].u]) {
                         conflict = true;
                         break;
                     }
                 }
                 if (!conflict) break;
                 k++;
             }
             colored_P[i] = {u, k};
        }
        
        // Sort candidates by color descending. 
        // This ordering aids in pruning: if we can't surpass maxQ with the highest color, we stop.
        sort(colored_P.begin(), colored_P.end(), [](const NodeInfo& a, const NodeInfo& b){
            return a.color > b.color;
        });
        
        // Iterate through candidates
        for (int i = 0; i < sz; ++i) {
            // Safety time check inside loop for cases with large candidate sets
            if (ops_counter > 1000 && (double)(clock() - start_time) / CLOCKS_PER_SEC > TIME_LIMIT) return;

            int u = colored_P[i].u;
            int c = colored_P[i].color;
            
            // Pruning: The max clique we can form extending Q with u is bounded by Q.size() + c
            // If this is not better than the best found so far, prune this branch.
            if (Q.size() + c <= maxQ.size()) {
                return;
            }
            
            // Add vertex to current clique
            Q.push_back(u);
            
            // Construct new candidate set: intersection of remaining candidates (neighbors of u)
            // To avoid duplicates and ensure validity, we only consider candidates that appeared 
            // AFTER the current one in the sort order (handled by logic: only consider subset of colored_P)
            // But effectively, we just take all valid neighbors from the specific subset we are processing.
            // Based on the specific coloring-sort logic (Tomita et al.), we consider neighbors in the suffix.
            
            vector<int> newP;
            newP.reserve(c); 
            
            for (int j = i + 1; j < sz; ++j) {
                int v = colored_P[j].u;
                if (adj[u][v]) {
                    newP.push_back(v);
                }
            }
            
            expand(newP);
            
            // Backtrack
            Q.pop_back();
        }
    }
};

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    start_time = clock();
    
    if (cin >> N >> M) {
        for (int i = 0; i < M; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u][v] = 1;
            adj[v][u] = 1;
        }
        
        MaxCliqueSolver solver;
        solver.run();
        
        // Prepare output array
        vector<int> result(N + 1, 0);
        for (int u : solver.maxQ) {
            result[u] = 1;
        }
        
        // Output result for each vertex
        for (int i = 1; i <= N; ++i) {
            cout << result[i] << "\n";
        }
    }
    return 0;
}