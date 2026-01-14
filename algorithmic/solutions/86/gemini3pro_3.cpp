#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <map>

using namespace std;

// Global variables
int N;
vector<int> parent;
vector<vector<int>> children;
vector<int> sz;
vector<bool> in_tree;
vector<bool> visited;

// Query function: 0 u v w returns median node
int query(int u, int v, int w) {
    cout << "0 " << u << " " << v << " " << w << endl;
    int res;
    cin >> res;
    return res;
}

// Function to add a child to a parent in the virtual tree
void add_child(int p, int c) {
    children[p].push_back(c);
    parent[c] = p;
}

// Function to insert a node 'new_node' between p and c
// Effectively splits the edge p->c into p->new_node->c
void split_edge(int p, int c, int new_node) {
    // Remove c from p's children
    auto& kids = children[p];
    kids.erase(remove(kids.begin(), kids.end(), c), kids.end());
    
    // Add new_node to p
    add_child(p, new_node);
    
    // Add c to new_node
    add_child(new_node, c);
    
    in_tree[new_node] = true;
    visited[new_node] = true;
    
    // Fix sizes
    // sz[c] is already correct
    sz[new_node] = sz[c] + 1;
    // Propagate size change up from p
    // sz[p] increased by 1 (due to new_node)
    int curr = p;
    while (curr != 0) {
        sz[curr]++;
        curr = parent[curr];
    }
}

// Insert node u into the tree
void insert_node(int u) {
    int curr = 1;
    int forbidden = -1;
    
    while (true) {
        // Find heavy path from curr, avoiding the 'forbidden' child if any
        vector<int> path;
        path.push_back(curr);
        
        // Construct heavy path
        while (true) {
            int best_c = -1;
            int max_s = -1;
            for (int c : children[path.back()]) {
                if (c == forbidden) continue; // Skip the child we just eliminated
                if (sz[c] > max_s) {
                    max_s = sz[c];
                    best_c = c;
                }
            }
            
            // forbidden is only for the immediate child of curr
            // Once we step down, we can pick any child
            if (path.size() == 1) forbidden = -1;
            
            if (best_c != -1) {
                path.push_back(best_c);
            } else {
                break;
            }
        }
        
        int leaf = path.back();
        if (leaf == curr) {
            // No children to traverse (or all forbidden), attach u here
            add_child(curr, u);
            in_tree[u] = true;
            visited[u] = true;
            sz[u] = 1;
            int temp = curr;
            while(temp != 0) {
                sz[temp]++;
                temp = parent[temp];
            }
            return;
        }
        
        // Query median of (root, u, leaf)
        // This gives the attachment point on the path 1..leaf
        int w = query(1, u, leaf);
        
        if (!in_tree[w]) {
            // w is a new node on the path curr...leaf
            // We need to insert w into the edge on the path.
            // Binary search to find where w splits the path.
            // path is p[0]...p[k], p[0]=curr, p[k]=leaf
            // We want largest i such that path[i] is ancestor of w.
            int L = 0, R = path.size() - 1;
            int best_i = 0;
            
            while (L <= R) {
                int mid = L + (R - L) / 2;
                if (path[mid] == w) {
                    best_i = mid;
                    break;
                }
                // Check ancestry: query(1, path[mid], w). If result is path[mid], then path[mid] is anc of w.
                if (query(1, path[mid], w) == path[mid]) {
                    best_i = mid;
                    L = mid + 1;
                } else {
                    R = mid - 1;
                }
            }
            
            // w is between path[best_i] and path[best_i+1]
            split_edge(path[best_i], path[best_i+1], w);
            
            // Now attach u to w
            if (u != w) {
                add_child(w, u);
                in_tree[u] = true;
                visited[u] = true;
                sz[u] = 1;
                int temp = w;
                while (temp != 0) {
                    sz[temp]++;
                    temp = parent[temp];
                }
            }
            return;
        } else {
            // w is already in tree. Since w is on path 1..leaf and also in subtree of curr,
            // w must be on the path we just constructed.
            // Find w index in path.
            int idx = -1;
            for(int i=0; i<path.size(); ++i) {
                if(path[i] == w) {
                    idx = i;
                    break;
                }
            }
            
            if (w == leaf) {
                // u attaches to leaf
                add_child(w, u);
                in_tree[u] = true;
                visited[u] = true;
                sz[u] = 1;
                int temp = w;
                while(temp != 0) {
                    sz[temp]++;
                    temp = parent[temp];
                }
                return;
            }
            
            // w is an internal node on path. u branches off at w.
            // But u is NOT in the subtree of path[idx+1] (the heavy child).
            // We need to restart search from w, but forbid path[idx+1].
            curr = w;
            forbidden = path[idx+1];
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;

    parent.resize(N + 1, 0);
    children.resize(N + 1);
    sz.resize(N + 1, 0);
    in_tree.resize(N + 1, false);
    visited.resize(N + 1, false);

    // Initial tree: node 1
    in_tree[1] = true;
    visited[1] = true;
    sz[1] = 1;
    parent[1] = 0;

    // Process nodes in random order to keep tree roughly balanced/avoid worst cases
    vector<int> p(N - 1);
    iota(p.begin(), p.end(), 2);
    random_shuffle(p.begin(), p.end());

    for (int u : p) {
        if (!visited[u]) {
            insert_node(u);
        }
    }

    cout << "1";
    for (int i = 2; i <= N; ++i) {
        cout << " " << i << " " << parent[i];
    }
    cout << endl;

    return 0;
}