#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Global variables to store graph and results
int N;
vector<int> adj[1005];       // Adjacency list for the graph
vector<int> sets[50];        // Independent sets for graph coloring / efficient querying
int love[1005];              // love[u] = v means u loves v
bool visited[1005];          // For outputting answers

// Function to perform a query
int query(const vector<int>& v) {
    if (v.empty()) return 0;
    cout << "Query " << v.size();
    for (int x : v) cout << " " << x;
    cout << endl; // Flushes output
    int res;
    cin >> res;
    return res;
}

// Recursive function to find edges between u and a subset of nodes
void find_edges(int u, const vector<int>& candidates) {
    // If we've already found 3 edges for u, we stop (max degree is 3)
    if (adj[u].size() >= 3) return;
    if (candidates.empty()) return;

    // Base case: if candidates size is 1, we found an edge
    if (candidates.size() == 1) {
        // Add edge undirected
        adj[u].push_back(candidates[0]);
        adj[candidates[0]].push_back(u);
        return;
    }

    // Divide and conquer
    int mid = candidates.size() / 2;
    vector<int> left_part(candidates.begin(), candidates.begin() + mid);
    vector<int> right_part(candidates.begin() + mid, candidates.end());

    // Check if there are edges in the left part
    vector<int> q_set = left_part;
    q_set.push_back(u);
    int res = query(q_set);
    if (res != (int)left_part.size() + 1) {
        find_edges(u, left_part);
    }
    
    // If we reached max degree, stop early
    if (adj[u].size() >= 3) return;

    // Check if there are edges in the right part
    vector<int> q_set_r = right_part;
    q_set_r.push_back(u);
    int res_r = query(q_set_r);
    if (res_r != (int)right_part.size() + 1) {
        find_edges(u, right_part);
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    
    if (!(cin >> N)) return 0;

    int num_sets = 0;

    // Step 1: Build the graph
    for (int i = 1; i <= 2 * N; ++i) {
        int placed_in_set = -1;
        
        // Check connectivity with existing independent sets
        for (int s = 0; s < num_sets; ++s) {
            if (adj[i].size() >= 3) break;
            
            vector<int> q_set = sets[s];
            q_set.push_back(i);
            int res = query(q_set);
            
            if (res == (int)sets[s].size() + 1) {
                // No edges between i and sets[s]
                // We can potentially place i in this set if we haven't placed it yet
                if (placed_in_set == -1) placed_in_set = s;
            } else {
                // There is at least one edge, find it/them
                find_edges(i, sets[s]);
            }
        }
        
        // Add i to an independent set
        if (placed_in_set != -1) {
            sets[placed_in_set].push_back(i);
        } else {
            // Create a new set
            sets[num_sets].push_back(i);
            num_sets++;
        }
    }

    // Step 2: Determine 'love' relationships
    // First pass: Nodes with degree 3 (generic case)
    for (int i = 1; i <= 2 * N; ++i) {
        if (adj[i].size() == 3) {
            int x = adj[i][0];
            int y = adj[i][1];
            int z = adj[i][2];
            
            // To identify who i loves, we query subsets of size 3
            // If i loves L(i), and we query {i, a, b}, the result is 1 iff {a, b} = {mate(i), loved_by(i)}
            // i.e., L(i) is excluded from the query.
            
            vector<int> q = {i, x, y};
            int res = query(q);
            if (res == 1) {
                love[i] = z;
            } else {
                q = {i, x, z};
                res = query(q);
                if (res == 1) {
                    love[i] = y;
                } else {
                    love[i] = x;
                }
            }
        }
    }
    
    // Second pass: Nodes with degree 2 (mutual love case)
    for (int i = 1; i <= 2 * N; ++i) {
        if (adj[i].size() == 2) {
            int u = i;
            // If love is already determined (by processing the partner), skip
            if (love[u] != 0) continue;

            int v1 = adj[u][0];
            int v2 = adj[u][1];
            
            // Check edge (u, v1). If result is 1, it's a mate edge. If 2, it's a mutual love edge.
            vector<int> q = {u, v1};
            int res = query(q);
            
            if (res == 1) {
                // v1 is mate, so v2 is lover
                love[u] = v2;
                love[v2] = u; // Symmetry for mutual love
            } else {
                // v1 is lover
                love[u] = v1;
                love[v1] = u; // Symmetry for mutual love
            }
        }
    }

    // Step 3: Determine mates and output answers
    for (int i = 1; i <= 2 * N; ++i) {
        if (visited[i]) continue;
        
        int mate = -1;
        
        if (adj[i].size() == 2) {
            // Degree 2: neighbors are {love[i], mate[i]}
            int l = love[i];
            for (int v : adj[i]) {
                if (v != l) {
                    mate = v;
                    break;
                }
            }
        } else {
            // Degree 3: neighbors are {love[i], loved_by[i], mate[i]}
            int l = love[i];
            vector<int> candidates;
            for (int v : adj[i]) {
                if (v != l) candidates.push_back(v);
            }
            
            // Candidates are {loved_by[i], mate[i]}
            // loved_by[i] is the node v such that love[v] == i
            // We check which candidate loves i
            int c1 = candidates[0];
            int c2 = candidates[1];
            
            if (love[c1] == i) {
                mate = c2;
            } else {
                mate = c1;
            }
        }
        
        cout << "Answer " << i << " " << mate << endl;
        visited[i] = true;
        visited[mate] = true;
    }

    return 0;
}