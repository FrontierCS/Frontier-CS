#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <map>

using namespace std;

// This is an interactive problem.
// We need to flush output after every command.
// For cout, `cout << ... << endl;` is sufficient.

int n;

// Since we swap elements, we need to track their original values.
// p_pos[v] = current position of original value v
// p_val[p] = current original value at position p
// Initially, value i is at position i.
vector<int> p_pos;
vector<int> p_val;

// Wrapper for query operation
int ask_query(int l, int r) {
    cout << "1 " << l << " " << r << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); // Error
    return res;
}

// Wrapper for swap operation, also updates our tracking arrays
void do_swap(int i, int j) {
    if (i == j) return;
    cout << "2 " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); // Error
    
    // Update tracking arrays
    swap(p_val[i], p_val[j]);
    p_pos[p_val[i]] = i;
    p_pos[p_val[j]] = j;
}

// A value-contiguous pair of elements p_i, p_j means |p_i - p_j| = 1.
// We can check this by querying the interval [i, j], which has 2 elements.
// The number of value-contiguous segments will be 3 if they are a pair, and 2 otherwise.
// This is not efficient for arbitrary i, j. Swapping is needed.

// A more powerful tool is to count edges between sets of nodes (positions).
// An "edge" exists between two positions if their values are consecutive.
// f(S) = number of edges with both endpoints in S.
// f(S) can be calculated by moving all elements from positions in S to a contiguous
// block, say [1, |S|], and querying. The query result `C(1, |S|)` is `|S| + f(S)`.
// `edges(S1, S2) = f(S1 U S2) - f(S1) - f(S2)`.

// This function calculates f(S) for a set of original values S.
// It costs 2*|S| swaps to move elements and restore them.
int count_internal_edges(const vector<int>& S) {
    if (S.size() <= 1) {
        return 0;
    }
    int k = S.size();
    
    // Store original state of the scratchpad area [1, k]
    vector<int> target_values_at_scratchpad;
    for (int i = 0; i < k; ++i) {
        target_values_at_scratchpad.push_back(p_val[i + 1]);
    }

    // Move elements of S to scratchpad area [1, k]
    for (int i = 0; i < k; ++i) {
        do_swap(i + 1, p_pos[S[i]]);
    }
    
    int result = ask_query(1, k) - k;

    // Restore the permutation to its state before this function call
    // by swapping the original scratchpad values back.
    for (int i = k - 1; i >= 0; --i) {
        do_swap(i + 1, p_pos[target_values_at_scratchpad[i]]);
    }
    
    return result;
}

// Calculates edges between a single node {u} and a set of nodes V_nodes.
int count_edges_to_set(int u, const vector<int>& V_nodes) {
    if (V_nodes.empty()) {
        return 0;
    }
    vector<int> u_and_V = V_nodes;
    u_and_V.push_back(u);
    
    int f_V = count_internal_edges(V_nodes);
    int f_uV = count_internal_edges(u_and_V);
    
    return f_uV - f_V;
}

vector<int> adj[1001];

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int l1, l2;
    cin >> n >> l1 >> l2;

    p_pos.resize(n + 1);
    p_val.resize(n + 1);
    iota(p_pos.begin() + 1, p_pos.end(), 1);
    iota(p_val.begin() + 1, p_val.end(), 1);
    
    // The main idea is to find the hidden path structure of the permutation.
    // The values `1, 2, ..., n` form a path. The positions where these values
    // are located thus form a path graph, where an edge means values are consecutive.
    // We find this path by finding neighbors for each node.
    
    // A sqrt decomposition approach to find neighbors for each node.
    // For each node `i`, we find its neighbors in `V\{i}`.
    // Partition `V\{i}` into blocks of size sqrt(n).
    // First, check which blocks contain neighbors.
    // Then, for each such block, find the specific neighbor.
    int block_size = sqrt(n);
    if (block_size == 0) block_size = 1;

    for (int i = 1; i <= n; ++i) {
        vector<int> others;
        for (int j = 1; j <= n; ++j) {
            if (i == j) continue;
            // Check if already found as a neighbor
            bool is_neighbor = false;
            for (int neighbor : adj[i]) {
                if (neighbor == j) {
                    is_neighbor = true;
                    break;
                }
            }
            if (!is_neighbor) {
                others.push_back(j);
            }
        }
        
        // A node can have at most 2 neighbors (unless n=1).
        while (adj[i].size() < 2 && !others.empty()) {
            vector<vector<int>> blocks;
            for (size_t j = 0; j < others.size(); j += block_size) {
                blocks.emplace_back();
                for (size_t k = j; k < others.size() && k < j + block_size; ++k) {
                    blocks.back().push_back(others[k]);
                }
            }
            
            vector<int> promising_block;
            for (const auto& block : blocks) {
                if (count_edges_to_set(i, block) > 0) {
                    promising_block = block;
                    break;
                }
            }
            
            if (!promising_block.empty()) {
                // Binary search for the neighbor in the promising block
                while(promising_block.size() > 1) {
                    vector<int> half;
                    for(size_t k=0; k < promising_block.size()/2; ++k) {
                        half.push_back(promising_block[k]);
                    }
                    if (count_edges_to_set(i, half) > 0) {
                        promising_block = half;
                    } else {
                        vector<int> other_half;
                        for(size_t k=promising_block.size()/2; k < promising_block.size(); ++k) {
                            other_half.push_back(promising_block[k]);
                        }
                        promising_block = other_half;
                    }
                }
                int neighbor = promising_block[0];
                adj[i].push_back(neighbor);
                adj[neighbor].push_back(i);
                
                // Update `others` list
                vector<int> new_others;
                for(int node : others) {
                    if (node != neighbor) {
                        new_others.push_back(node);
                    }
                }
                others = new_others;
            } else {
                // No more neighbors
                break;
            }
        }
    }

    // After building adj list, find an endpoint (degree 1 node) and traverse
    int start_node = -1;
    if (n > 0) start_node = 1;
    for (int i = 1; i <= n; ++i) {
        if (adj[i].size() == 1) {
            start_node = i;
            break;
        }
    }
    
    vector<int> path;
    if (start_node != -1) {
        vector<int> q;
        q.push_back(start_node);
        vector<bool> visited(n + 1, false);
        visited[start_node] = true;
        int head = 0;
        while(head < (int)q.size()){
            int u = q[head++];
            path.push_back(u);
            for(int v : adj[u]){
                if(!visited[v]){
                    visited[v] = true;
                    q.push_back(v);
                }
            }
        }
    }

    // We found the path of positions. Assign values 1..n along this path.
    // This gives one of the two indistinguishable permutations.
    vector<int> p_ans(n + 1);
    for (int i = 0; i < n; ++i) {
        p_ans[path[i]] = i + 1;
    }
    
    cout << "3";
    for (int i = 1; i <= n; ++i) {
        cout << " " << p_ans[i];
    }
    cout << endl;

    return 0;
}