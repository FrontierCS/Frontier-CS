#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>

using namespace std;

// Global variables to store circuit info
int N, R;
struct Gate {
    int id;
    int u, v; // inputs
    int type; // 0 for AND, 1 for OR, -1 for unknown
};
vector<Gate> gates;
vector<int> parent;
vector<int> is_left_child; // 1 if left child of parent, 0 if right
vector<vector<int>> adj;   // Children in the tree structure (inverse of input wiring)
vector<int> depth;
vector<int> heavy;         // Heavy child
vector<int> head;          // Head of heavy chain
vector<int> pos_in_chain;  // Position in chain

// Helper to interact with the judge
int query(const string& s) {
    cout << "? " << s << endl;
    int res;
    cin >> res;
    return res;
}

// Function to set up the string s based on desired logic
// We want to test a specific set of gates or path.
// desired_val[i] = {v, active}
// If active, we try to force output of i to v.
// If i is a leaf (>= N), we just set s[i] = v.
// If i is a gate (< N), we set s[i] such that output becomes v.
// To do this for a gate, we assume its inputs are set to (0,0) so it outputs 0 naturally.
// Then s[i] = v.
// This requires setting the entire subtree of i to "0-mode".

// Global state for a query construction
string current_s;
vector<int> node_mode; // 0: force 0, 1: force 1, 2: pass-through (sensitized)

// To efficiently manage, we will construct s for each query from scratch.
// Strategy:
// 1. Initialize all leaf switches to 0. All gate switches to 0.
//    This essentially tries to make everything 0.
// 2. Modify specific switches to sensitize paths or set values.

void set_subtree_zero(int u, string& s) {
    // For leaves, set s[u] = 0.
    // For gates, set s[u] = 0. Inputs will be 0 (recursively), so AND/OR(0,0)=0.
    // So output is 0.
    // This is the default state if s is all '0'.
    // So we don't need to do anything if we start with '00...0'.
}

// Set a node u to output val (0 or 1). Assumes u's inputs are (0,0).
void set_node_value(int u, int val, string& s) {
    if (u >= N) {
        s[u] = (val ? '1' : '0');
    } else {
        // Gate u. Inputs are 0,0 -> Gate logic 0.
        // Output = 0 ^ s[u]. We want val.
        s[u] = (val ? '1' : '0');
    }
}

// Prepare sensitization for a node u.
// We need to set side inputs of ancestors to non-controlling values.
// We assume we know the types of ancestors.
void sensitize_path(int u, string& s) {
    int curr = u;
    while (curr != 0) {
        int p = parent[curr];
        int sibling = (is_left_child[curr] ? gates[p].v : gates[p].u);
        
        // Determine required value for sibling
        // If parent is AND (0), need 1.
        // If parent is OR (1), need 0.
        int p_type = gates[p].type;
        int req_val = (p_type == 0 ? 1 : 0);
        
        set_node_value(sibling, req_val, s);
        
        // Also ensure s[p] = 0 so it doesn't flip the signal
        s[p] = '0'; 
        
        curr = p;
    }
    // Also ensure root s[0] = 0
    s[0] = '0';
}

// Solve a chain [u, ... , v] where u is highest (closest to root), v is lowest.
// Chain nodes are connected: u is parent of ... parent of v.
// Specifically, next in chain is the heavy child.
void solve_chain(const vector<int>& chain) {
    if (chain.empty()) return;
    
    // Function to check a range [l, r] in chain assuming all are type assumed_type
    // Returns true if assumption is consistent
    auto check = [&](int l, int r, int assumed_type) -> bool {
        string s(2 * N + 1, '0');
        
        // Sensitize path from chain head (chain[0]) to root
        sensitize_path(chain[0], s);
        
        // For nodes in range [l, r], set side inputs to allow propagation
        // If assumed AND -> side=1. If OR -> side=0.
        int side_val = (assumed_type == 0 ? 1 : 0);
        
        for (int i = l; i <= r; ++i) {
            int u = chain[i];
            int heavy_child = -1;
            if (i < (int)chain.size() - 1) heavy_child = chain[i+1];
            
            // Side child is the non-heavy one
            int child_u = gates[u].u;
            int child_v = gates[u].v;
            int side_child = (child_u == heavy_child ? child_v : child_u);
            
            set_node_value(side_child, side_val, s);
            s[u] = '0'; // Pass through
        }
        
        // For nodes above l in chain (if any), we already know types.
        for (int i = 0; i < l; ++i) {
            int u = chain[i];
            int p_type = gates[u].type;
            int req = (p_type == 0 ? 1 : 0);
            int heavy_child = chain[i+1];
            int side_child = (gates[u].u == heavy_child ? gates[u].v : gates[u].u);
            set_node_value(side_child, req, s);
            s[u] = '0';
        }

        // Input to the bottom of the tested range (chain[r])
        // To check for 'assumed_type', we feed input such that 'assumed_type' passes but 'other' flips.
        // If assumed AND: input (0,1). Side is 1. Input bottom 0.
        // AND(0,1) -> 0. OR(0,1) -> 1.
        // So expected 0. If 1, mismatch.
        // If assumed OR: input (1,0). Side is 0. Input bottom 1.
        // OR(1,0) -> 1. AND(1,0) -> 0.
        // So expected 1. If 0, mismatch.
        
        int bottom_node = chain[r];
        int next_input = -1;
        // The heavy child of bottom_node is not in the tested range.
        if (r < (int)chain.size() - 1) next_input = chain[r+1];
        else {
            // Find which input is heavy (conceptually, the one extending the chain)
            // But here the chain ends. We pick the input corresponding to heavy direction if we had one?
            // Actually, we just pick the one that ISN'T the side child we just set.
            // We defined side_child above.
            // Wait, for bottom node, we need to set its input.
            // In the loop above, we set side child of chain[r].
            // We need to set the MAIN input of chain[r] (the one that would continue the chain).
            // Since we stored heavy child, let's use that logic.
            // But at the end of chain, maybe both are light?
            // HLD: chain ends when next is not heavy.
            // So chain[r] has children, neither is in chain.
            // We arbitrarily picked one as side in the loop?
            // No, the loop logic: "int side_child = (child_u == heavy_child ? child_v : child_u);"
            // For the last element, heavy_child is -1 (from code above).
            // So side_child is child_v (arbitrary).
            // Main input is child_u.
            int child_u = gates[bottom_node].u;
            // int child_v = gates[bottom_node].v;
            // side was child_v.
             next_input = child_u;
        }
        
        int input_val = (assumed_type == 0 ? 0 : 1);
        set_node_value(next_input, input_val, s);
        
        // Expected output at root:
        // If match, signal passes unchanged (or rather, consistent with types).
        // Since we force s=0 along path, and sensitize correct side inputs:
        // Value at chain[r] output should be input_val.
        // Then it propagates up to chain[0].
        // Then propagates up to root.
        // NOTE: Path from chain[0] to root might invert signal if we have s[p]=1?
        // But we set s[p]=0 in sensitize_path.
        // What about gate logic?
        // AND(0, 1) = 0 (pass 0). OR(1, 0) = 1 (pass 1).
        // So value is preserved.
        // So expected root value = input_val.
        
        int res = query(s);
        return res == input_val;
    };

    auto assign_range = [&](int l, int r, int type) {
        for(int i=l; i<=r; ++i) gates[chain[i]].type = type;
    };

    // Recursive solver
    auto solve_range = [&](auto&& self, int l, int r) -> void {
        if (l > r) return;
        if (l == r) {
            // Single node, test if AND
            if (check(l, l, 0)) gates[chain[l]].type = 0;
            else gates[chain[l]].type = 1;
            return;
        }
        
        // Try assuming all AND
        if (check(l, r, 0)) {
            assign_range(l, r, 0);
            return;
        }
        // Try assuming all OR
        if (check(l, r, 1)) {
            assign_range(l, r, 1);
            return;
        }
        
        // Split
        int mid = (l + r) / 2;
        self(self, l, mid);
        self(self, mid + 1, r);
    };

    solve_range(solve_range, 0, (int)chain.size() - 1);
}


// DFS for HLD setup
int dfs_sz(int u) {
    if (u >= N) return 1;
    int sz = 1;
    int max_sz = 0;
    
    // Check children
    int v1 = gates[u].u;
    int s1 = dfs_sz(v1);
    sz += s1;
    if (s1 > max_sz) {
        max_sz = s1;
        heavy[u] = v1;
    }
    
    int v2 = gates[u].v;
    int s2 = dfs_sz(v2);
    sz += s2;
    if (s2 > max_sz) {
        max_sz = s2;
        heavy[u] = v2;
    }
    
    return sz;
}

int main() {
    if (!(cin >> N >> R)) return 0;
    
    gates.resize(N);
    parent.assign(2 * N + 1, -1);
    is_left_child.assign(2 * N + 1, -1);
    adj.resize(N);
    heavy.assign(2 * N + 1, -1);
    
    // Inputs are N lines. 
    // Problem says: "For i = N-1, N-2, ..., 0 ... Ui Vi".
    for (int i = N - 1; i >= 0; --i) {
        cin >> gates[i].u >> gates[i].v;
        gates[i].id = i;
        gates[i].type = -1;
        
        parent[gates[i].u] = i;
        is_left_child[gates[i].u] = 1; // Arbitrary: u is left
        
        parent[gates[i].v] = i;
        is_left_child[gates[i].v] = 0; // v is right
    }
    
    // Build HLD
    dfs_sz(0);
    
    // Extract chains and solve
    // We traverse in topological order (or reverse post-order).
    // Actually, simply BFS/DFS to find chain heads.
    // Chain head is node where parent is not linking via heavy edge.
    // Root is always chain head.
    
    vector<int> q;
    q.push_back(0);
    vector<vector<int>> chains;
    
    // Collect all chains
    // We can just iterate nodes 0..N-1. If u is head, trace chain.
    // u is head if u==0 or parent[u]'s heavy child != u.
    // But we need to solve chains in top-down order.
    // A chain can be solved once its head's parent is solved (to sensitize).
    
    // Queue of chain heads
    vector<int> chain_heads;
    chain_heads.push_back(0);
    
    int head_idx = 0;
    while(head_idx < (int)chain_heads.size()){
        int u = chain_heads[head_idx++];
        vector<int> chain;
        int curr = u;
        while(curr < N) {
            chain.push_back(curr);
            // Add light children of curr to queue
            int v1 = gates[curr].u;
            int v2 = gates[curr].v;
            if (heavy[curr] == v1) {
                if (v2 < N) chain_heads.push_back(v2);
                curr = v1;
            } else {
                if (v1 < N) chain_heads.push_back(v1);
                curr = v2;
            }
            if (curr >= N) break; // End of chain
            // If curr is not heavy child of prev, loop would break?
            // No, inside while we follow heavy edge.
        }
        solve_chain(chain);
    }
    
    string ans = "";
    for (int i = 0; i < N; ++i) {
        ans += (gates[i].type == 0 ? '&' : '|');
    }
    cout << "! " << ans << endl;
    
    return 0;
}