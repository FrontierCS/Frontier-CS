#include <bits/stdc++.h>
using namespace std;

int n;
vector<vector<int>> adj;
vector<int> parent;
vector<int> depth;
int query_count = 0;

int query(int a, int b, int c) {
    cout << "0 " << a << " " << b << " " << c << endl;
    query_count++;
    int res;
    cin >> res;
    return res;
}

void add_edge(int u, int v) {
    adj[u].push_back(v);
    adj[v].push_back(u);
    parent[v] = u;
    depth[v] = depth[u] + 1;
}

// Get nodes in the subtree of 'root' (including root) that are in the active set.
// It traverses without going above 'root' (i.e., ignores the parent of root).
vector<int> get_subtree(int root, const vector<bool>& active) {
    vector<int> res;
    stack<int> st;
    vector<bool> vis(n+1, false);
    st.push(root);
    vis[root] = true;
    while (!st.empty()) {
        int v = st.top(); st.pop();
        res.push_back(v);
        for (int to : adj[v]) {
            if (active[to] && !vis[to] && to != parent[v]) {
                vis[to] = true;
                st.push(to);
            }
        }
    }
    return res;
}

// Find a centroid of the active tree.
int find_centroid(const vector<bool>& active, int banned = -1) {
    // Find first active node
    int root = -1;
    for (int i = 1; i <= n; i++) if (active[i]) { root = i; break; }
    
    vector<int> subsize(n+1, 0);
    vector<int> par_cent(n+1, -1);
    function<void(int,int)> dfs1 = [&](int v, int p) {
        par_cent[v] = p;
        subsize[v] = 1;
        for (int to : adj[v]) {
            if (!active[to] || to == p) continue;
            dfs1(to, v);
            subsize[v] += subsize[to];
        }
    };
    dfs1(root, -1);
    int total = subsize[root];
    
    int best_node = root;
    int best_max = total;
    for (int v = 1; v <= n; v++) {
        if (!active[v]) continue;
        if (v == banned) continue;
        int max_comp = 0;
        for (int to : adj[v]) {
            if (!active[to]) continue;
            if (to == par_cent[v]) {
                max_comp = max(max_comp, total - subsize[v]);
            } else {
                max_comp = max(max_comp, subsize[to]);
            }
        }
        if (max_comp < best_max) {
            best_max = max_comp;
            best_node = v;
        }
    }
    return best_node;
}

// Find child of 'm' that lies on the path to 'c' (m is ancestor of c).
int find_child_on_path(int m, int c) {
    int cur = c;
    while (parent[cur] != m) cur = parent[cur];
    return cur;
}

// Find parent for a new node u (the tree currently consists of nodes 1..u-1)
int find_parent(int u) {
    vector<bool> active(n+1, false);
    for (int i = 1; i < u; i++) active[i] = true;
    int num_active = u-1;
    
    // To avoid infinite loops, keep track of previous centroid
    int prev_centroid = -1;
    
    while (num_active > 1) {
        int c = find_centroid(active, prev_centroid);
        if (c == 1) {
            // Ensure c != 1 for the query
            for (int i = 2; i < u; i++) if (active[i]) { c = i; break; }
        }
        int m = query(u, 1, c);
        
        if (m == 1) {
            vector<int> to_remove = get_subtree(c, active);
            for (int x : to_remove) active[x] = false;
            num_active -= to_remove.size();
            prev_centroid = -1; // reset
        } else if (m == c) {
            vector<int> to_keep = get_subtree(c, active);
            // Check if active set would remain the same
            if (to_keep.size() == num_active) {
                // This centroid didn't reduce the set; ban it and try another
                prev_centroid = c;
                continue;
            }
            for (int i = 1; i < u; i++) if (active[i]) active[i] = false;
            for (int x : to_keep) active[x] = true;
            num_active = to_keep.size();
            prev_centroid = -1;
        } else {
            int child_mc = find_child_on_path(m, c);
            vector<int> subtree_m = get_subtree(m, active);
            vector<int> subtree_child = get_subtree(child_mc, active);
            set<int> child_set(subtree_child.begin(), subtree_child.end());
            vector<int> to_keep;
            for (int x : subtree_m) if (!child_set.count(x)) to_keep.push_back(x);
            if (to_keep.size() == num_active) {
                prev_centroid = c;
                continue;
            }
            for (int i = 1; i < u; i++) if (active[i]) active[i] = false;
            for (int x : to_keep) active[x] = true;
            num_active = to_keep.size();
            prev_centroid = -1;
        }
    }
    
    for (int i = 1; i < u; i++) if (active[i]) return i;
    return -1; // should not happen
}

int main() {
    cin >> n;
    adj.resize(n+1);
    parent.resize(n+1);
    depth.resize(n+1);
    
    if (n == 3) {
        int m = query(1, 2, 3);
        if (m == 1) {
            cout << "1 1 2 1 3" << endl;
        } else if (m == 2) {
            cout << "1 2 1 2 3" << endl;
        } else {
            cout << "1 3 1 3 2" << endl;
        }
        return 0;
    }
    
    // Build initial tree with nodes 1,2,3
    int m = query(1, 2, 3);
    if (m == 1) {
        add_edge(1, 2);
        add_edge(1, 3);
    } else if (m == 2) {
        add_edge(2, 1);
        add_edge(2, 3);
        // Set root to 1 still, but we need to adjust parent? Actually we set root=1 globally.
        // But if we added edges 2-1 and 2-3, then parent[1]=2, which contradicts root=1.
        // To keep root=1, we should orient edges accordingly.
        // We'll simply set parent[1]=0, parent[2]=1, parent[3]=2? That would be a different tree.
        // Instead, we rebuild the tree with correct orientation.
        // Since the tree is undirected, we can just store edges and later output them.
        // But for our algorithm we need a rooted tree at 1.
        // So we should re-root the tree at 1.
        // We'll clear and add edges with 1 as root.
        adj.clear(); adj.resize(n+1);
        parent.assign(n+1,0);
        depth.assign(n+1,0);
        adj[1].push_back(2); adj[2].push_back(1); parent[2]=1; depth[2]=1;
        adj[2].push_back(3); adj[3].push_back(2); parent[3]=2; depth[3]=2;
    } else {
        adj.clear(); adj.resize(n+1);
        parent.assign(n+1,0);
        depth.assign(n+1,0);
        adj[1].push_back(3); adj[3].push_back(1); parent[3]=1; depth[3]=1;
        adj[3].push_back(2); adj[2].push_back(3); parent[2]=3; depth[2]=2;
    }
    
    // Add remaining nodes
    for (int u = 4; u <= n; u++) {
        int p = find_parent(u);
        add_edge(p, u);
    }
    
    // Output the tree
    cout << "1";
    for (int u = 2; u <= n; u++) {
        cout << " " << parent[u] << " " << u;
    }
    cout << endl;
    
    return 0;
}