#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Global to store parent array and tree structure
// N <= 3000
int parent[3005];
int heavy[3005]; // heavy child (first attached child)
vector<int> lights[3005]; // light children (subsequent children)
int n;

// Function to query the black box
// Protocol: ? sz v1 v2 ...
int query(const vector<int>& nodes) {
    cout << "? " << nodes.size();
    for (int x : nodes) {
        cout << " " << x;
    }
    cout << endl;
    int res;
    cin >> res;
    return res;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int ty;
    if (!(cin >> n >> ty)) return 0;

    if (n == 1) {
        cout << "! 0" << endl;
        return 0;
    }

    // Step 1: Calculate R(u) for all u to determine topological order
    // R(u) = N - query(u, all others)
    // The query result for {u} U {others} is 1 + #unrelated.
    // Total nodes N = 1 (u) + #related_excluding_u + #unrelated
    // ans = 1 + N - 1 - #related_excluding_u
    // #related_excluding_u = N - ans
    // R(u) = #related = N - ans + 1. 
    // Since we sort, we can just use (N - ans) or (-ans).
    // Higher R means "higher" in tree (closer to root).
    
    vector<pair<int, int>> r_vals(n);

    for (int i = 1; i <= n; ++i) {
        vector<int> q_vec;
        q_vec.reserve(n);
        q_vec.push_back(i);
        for (int j = 1; j <= n; ++j) {
            if (i != j) q_vec.push_back(j);
        }
        int ans = query(q_vec);
        r_vals[i-1] = {N - ans, i};
    }

    // Sort nodes by R descending. 
    // Property: R(parent) > R(child) strictly because internal nodes have >= 2 children.
    sort(r_vals.begin(), r_vals.end(), [](const pair<int, int>& a, const pair<int, int>& b) {
        return a.first > b.first;
    });

    // The node with max R is the root.
    int root = r_vals[0].second;
    parent[root] = 0;
    
    // Initialize structure
    for(int i=1; i<=n; ++i) heavy[i] = 0;

    // Step 2: Insert nodes one by one in topological order
    for (int i = 1; i < n; ++i) {
        int u = r_vals[i].second;
        int curr = root;

        // Traverse down from root to find parent
        while (true) {
            // Identify the heavy chain starting at curr
            // A heavy chain consists of heavy edges: curr -> heavy[curr] -> heavy[heavy[curr]] ...
            vector<int> chain;
            int temp = curr;
            while (temp != 0) {
                chain.push_back(temp);
                temp = heavy[temp];
            }

            int branch_node = -1;
            
            // If chain has only curr, we must branch from curr
            if (chain.size() == 1) {
                branch_node = curr;
            } else {
                // Check if u is below the tail of the chain
                // Query order: tail, ..., curr, u
                // If u is descendant of tail, greedy picks tail, skips rest including u => Res 1
                // If u is not descendant of tail, greedy picks tail, picks u => Res 2
                int tail = chain.back();
                
                vector<int> q_chain;
                q_chain.reserve(chain.size() + 1);
                for (int k = chain.size() - 1; k >= 0; --k) q_chain.push_back(chain[k]);
                q_chain.push_back(u);
                
                int res = query(q_chain);
                if (res == 1) {
                    branch_node = tail;
                } else {
                    // u branches off somewhere in the middle of the chain
                    // Binary search to find the deepest node p in chain such that u is descendant of p
                    // We know u is below chain[0] (curr)
                    // We know u is NOT below chain.back()
                    int L = 0, R = chain.size() - 2;
                    int ans_idx = 0;
                    while (L <= R) {
                        int mid = L + (R - L) / 2;
                        // Query: chain[mid], ..., chain[0], u
                        vector<int> sub_q;
                        sub_q.reserve(mid + 2);
                        for (int k = mid; k >= 0; --k) sub_q.push_back(chain[k]);
                        sub_q.push_back(u);
                        
                        if (query(sub_q) == 1) {
                            ans_idx = mid;
                            L = mid + 1;
                        } else {
                            R = mid - 1;
                        }
                    }
                    branch_node = chain[ans_idx];
                }
            }

            curr = branch_node;
            
            // Now u is a descendant of 'curr' and NOT a descendant of 'heavy[curr]' (if heavy exists and we stopped earlier)
            // or u is descendant of tail.
            // Check if u is a new child of curr or belongs to one of the light subtrees.
            
            if (heavy[curr] == 0) {
                // No children yet, u becomes the first (heavy) child
                heavy[curr] = u;
                parent[u] = curr;
                break;
            } 
            
            // If we are here, curr has a heavy child, but u is not in its subtree.
            // Check light children.
            if (lights[curr].empty()) {
                lights[curr].push_back(u);
                parent[u] = curr;
                break;
            }

            // Check if u is related to ANY of the light children subtrees
            vector<int> q_l;
            q_l.reserve(lights[curr].size() + 1);
            for (int x : lights[curr]) q_l.push_back(x);
            q_l.push_back(u);
            
            // All light children are disjoint. Greedy picks all of them.
            // Then checks u. If u related to one, it is skipped -> size = K
            // If u unrelated to all, it is added -> size = K + 1
            int l_res = query(q_l);

            if (l_res == (int)lights[curr].size() + 1) {
                // Unrelated to all existing light children -> New light child
                lights[curr].push_back(u);
                parent[u] = curr;
                break;
            } else {
                // Related to one of the light children. Find which one.
                int L_idx = 0, R_idx = lights[curr].size() - 1;
                int target = -1;
                while (L_idx < R_idx) {
                    int mid = L_idx + (R_idx - L_idx) / 2;
                    vector<int> sub;
                    for (int k = L_idx; k <= mid; ++k) sub.push_back(lights[curr][k]);
                    sub.push_back(u);
                    
                    // sub contains subset of lights + u.
                    // If result is subset.size() - 1, then u is related to one in this subset.
                    if (query(sub) == (int)sub.size() - 1) {
                        R_idx = mid;
                    } else {
                        L_idx = mid + 1;
                    }
                }
                target = lights[curr][L_idx];
                curr = target;
                // Descend into this light child and repeat loop
            }
        }
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << parent[i];
    }
    cout << endl;

    return 0;
}