#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Global variables to store graph and love information
int N;
vector<int> adj[1005]; // Adjacency list for graph G
int love[1005];        // love[u] = v means u loves v
bool is_love[1005];    // true if we have identified who u loves

// Function to perform a query
int query(const vector<int>& v) {
    if (v.empty()) return 0;
    cout << "Query " << v.size();
    for (int x : v) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Recursive function to find edges between u and a set of candidates
// cand: list of vertices (assumed to be an independent set in G)
// u: the vertex we are connecting
// out: vector to store found neighbors
void find_edges(const vector<int>& cand, int u, vector<int>& out) {
    // Optimization: A node has at most 3 neighbors in total.
    // Since all neighbors must be in the other partition, if we found 3, we are done.
    if (out.size() >= 3) return;

    // Check if there are any edges between u and cand
    // Construct query set: cand + {u}
    vector<int> q = cand;
    q.push_back(u);
    int res = query(q);
    
    // If result == |cand| + 1, it means u introduced a new distinct color and
    // didn't interact with any node in cand (no edges in G).
    if (res == (int)cand.size() + 1) {
        return;
    }
    
    // Base case: single candidate found
    if (cand.size() == 1) {
        out.push_back(cand[0]);
        return;
    }
    
    // Divide and conquer
    int mid = cand.size() / 2;
    vector<int> left_part(cand.begin(), cand.begin() + mid);
    vector<int> right_part(cand.begin() + mid, cand.end());
    
    find_edges(left_part, u, out);
    find_edges(right_part, u, out);
}

int main() {
    // Interactive problem setup
    if (!(cin >> N)) return 0;
    
    // Part 1: Build the graph G
    // G is bipartite. We maintain two independent sets s0 and s1.
    // For each vertex, we search for neighbors in s0. If found, it belongs to s1.
    // If not found in s0, we search s1. It belongs to s0.
    vector<int> s0, s1;
    
    for (int i = 1; i <= 2 * N; ++i) {
        vector<int> neighbors;
        
        // Check s0
        find_edges(s0, i, neighbors);
        
        if (!neighbors.empty()) {
            // Neighbors found in s0, so i belongs to s1
            s1.push_back(i);
            for (int v : neighbors) {
                adj[i].push_back(v);
                adj[v].push_back(i);
            }
        } else {
            // No neighbors in s0, must search s1
            find_edges(s1, i, neighbors);
            // i belongs to s0
            s0.push_back(i);
            for (int v : neighbors) {
                adj[i].push_back(v);
                adj[v].push_back(i);
            }
        }
    }
    
    // Part 2: Resolve love directions for nodes with degree 3
    // Nodes with degree 1 are involved in mutual love, so only the same-color edge exists in G.
    // Nodes with degree 3 have edges to s(u), L(u), and L^-1(u).
    for (int i = 1; i <= 2 * N; ++i) {
        if (adj[i].size() == 3) {
            int x = adj[i][0];
            int y = adj[i][1];
            int z = adj[i][2];
            
            // To identify L(i), we use the property:
            // Res({i, s(i), L^-1(i)}) = 1
            // Res({i, s(i), L(i)}) = 2
            // Res({i, L(i), L^-1(i)}) = 2
            // The pair in neighbors that gives 1 is {s(i), L^-1(i)}. The excluded one is L(i).
            
            int res = query({i, x, y});
            if (res == 1) {
                love[i] = z;
            } else {
                int res2 = query({i, x, z});
                if (res2 == 1) {
                    love[i] = y;
                } else {
                    love[i] = x;
                }
            }
            is_love[i] = true;
        }
    }
    
    // Part 3: Output answers
    vector<bool> used(2 * N + 1, false);
    for (int i = 1; i <= 2 * N; ++i) {
        if (used[i]) continue;
        
        int partner = -1;
        if (adj[i].size() == 1) {
            // If degree 1, the only neighbor is the same-color partner
            partner = adj[i][0];
        } else {
            // If degree 3, remove L(i) and L^-1(i) from neighbors
            for (int v : adj[i]) {
                if (is_love[i] && love[i] == v) continue; // v is L(i)
                if (is_love[v] && love[v] == i) continue; // v loves i, so v is L^-1(i)
                partner = v;
                break;
            }
        }
        
        cout << "Answer " << i << " " << partner << endl;
        used[i] = true;
        used[partner] = true;
    }
    
    return 0;
}