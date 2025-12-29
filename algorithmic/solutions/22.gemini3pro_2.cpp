#include <iostream>
#include <vector>
#include <algorithm>
#include <set>

using namespace std;

const int MAXN = 100005;

// Graph structure
vector<int> adj[MAXN];
int parent_node[MAXN];
int L[MAXN], R[MAXN];
bool is_leaf[MAXN];
int N;

// Decomposition tree structure
struct Bag {
    set<int> elements;
    int id;
};

vector<Bag> bags;
vector<pair<int, int>> tree_edges;
int bag_counter = 0;

// Helper to create a new bag
int create_bag(const vector<int>& elems) {
    bag_counter++;
    Bag b;
    b.id = bag_counter;
    for (int x : elems) b.elements.insert(x);
    bags.push_back(b);
    return bag_counter;
}

// Helper to add edge in decomposition tree
void add_edge(int u, int v) {
    tree_edges.push_back({u, v});
}

// DFS to setup L, R and parent pointers
void dfs_prep(int u, int p) {
    parent_node[u] = p;
    bool leaf = true;
    L[u] = 1e9;
    R[u] = -1e9;
    
    for (int v : adj[u]) {
        if (v == p) continue;
        leaf = false;
        dfs_prep(v, u);
        L[u] = min(L[u], L[v]);
        R[u] = max(R[u], R[v]);
    }
    
    if (leaf) {
        is_leaf[u] = true;
        L[u] = u;
        R[u] = u;
    }
}

// Recursive function to build the decomposition
int build(int u) {
    // Identify children
    vector<int> children;
    for (int v : adj[u]) {
        if (v == parent_node[u]) continue;
        children.push_back(v);
    }
    
    // Leaf case
    if (children.empty()) {
        // Bag {u, p(u)} covers tree edge (u, p(u))
        return create_bag({u, parent_node[u]});
    }
    
    // Internal node case
    // Recursively build children
    vector<int> child_bags;
    child_bags.reserve(children.size());
    for (int v : children) {
        child_bags.push_back(build(v));
    }
    
    int m = children.size();
    int l_v1 = L[children[0]];
    
    int prev_k = -1;
    
    for (int i = 0; i < m; ++i) {
        int v_i = children[i];
        int r_vi = R[v_i];
        
        // K_i bag: main spine bag for child i
        // Contains u, L of first child, L of current child, R of current child
        int k_id = create_bag({u, l_v1, L[v_i], r_vi});
        
        // Connect child's structure to this spine node
        add_edge(k_id, child_bags[i]);
        
        if (i > 0) {
            // J_{i-1} bag: join bag between child i-1 and i
            // Connects R of prev child and L of current child (cycle edge)
            int r_prev = R[children[i-1]];
            int l_curr = L[children[i]];
            
            int j_id = create_bag({u, l_v1, r_prev, l_curr});
            
            add_edge(prev_k, j_id);
            add_edge(j_id, k_id);
        }
        
        prev_k = k_id;
    }
    
    // If u is root, K_m is the root of decomposition
    // It covers (u, L_v1, R_vm), where (R_vm, L_v1) is the closing cycle edge
    if (u == 1) {
        return prev_k;
    } else {
        // If u is not root, we need to provide interface to p(u)
        // Interface bag Fin = {u, p(u), L_u, R_u}
        // L_u = L_v1, R_u = R_vm
        int fin_id = create_bag({u, parent_node[u], L[u], R[u]});
        add_edge(prev_k, fin_id);
        return fin_id;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N)) return 0;
    
    for (int i = 0; i < N - 1; ++i) {
        int p;
        cin >> p;
        int u = p;
        int v = i + 2;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    // Sort adjacency lists to ensure planar ordering
    for (int i = 1; i <= N; ++i) {
        sort(adj[i].begin(), adj[i].end());
    }
    
    dfs_prep(1, 0);
    build(1);
    
    cout << bags.size() << "\n";
    for (const auto& b : bags) {
        cout << b.elements.size();
        for (int x : b.elements) {
            cout << " " << x;
        }
        cout << "\n";
    }
    
    for (const auto& e : tree_edges) {
        cout << e.first << " " << e.second << "\n";
    }
    
    return 0;
}