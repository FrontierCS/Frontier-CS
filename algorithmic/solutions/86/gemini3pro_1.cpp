#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <random>

using namespace std;

int N;
map<int, vector<int>> adj;
map<int, int> parent;
map<int, int> sz;
vector<bool> in_tree;

int query(int u, int v, int w) {
    cout << "0 " << u << " " << v << " " << w << endl;
    int res;
    cin >> res;
    return res;
}

// Update sizes upwards
void update_size_up(int u, int amount) {
    while (u != 0) {
        sz[u] += amount;
        u = parent[u];
    }
}

// Find heavy child
int get_heavy(int u, int p) {
    int max_s = -1;
    int heavy = -1;
    for (int v : adj[u]) {
        if (v != p) {
            if (sz[v] > max_s) {
                max_s = sz[v];
                heavy = v;
            }
        }
    }
    return heavy;
}

// Get the path from u downwards through heavy children to a leaf
void get_heavy_path(int u, int p, vector<int>& path) {
    path.push_back(u);
    int h = get_heavy(u, p);
    if (h != -1) {
        get_heavy_path(h, u, path);
    }
}

void add_edge(int u, int v) {
    adj[u].push_back(v);
    adj[v].push_back(u);
    parent[v] = u; 
    sz[v] = 1; // Initial size
    update_size_up(u, 1);
}

void split_edge_and_add(int u, int v, int mid, int new_leaf) {
    // Edge (u, v) exists, u is parent of v
    // Replace with (u, mid) and (mid, v)
    // Also attach new_leaf to mid
    
    // Remove v from u's children
    auto& neighbors_u = adj[u];
    neighbors_u.erase(remove(neighbors_u.begin(), neighbors_u.end(), v), neighbors_u.end());
    // Remove u from v's neighbors
    auto& neighbors_v = adj[v];
    neighbors_v.erase(remove(neighbors_v.begin(), neighbors_v.end(), u), neighbors_v.end());
    
    // Add edges
    adj[u].push_back(mid);
    adj[mid].push_back(u);
    
    adj[mid].push_back(v);
    adj[v].push_back(mid);
    
    adj[mid].push_back(new_leaf);
    adj[new_leaf].push_back(mid);
    
    parent[v] = mid;
    parent[mid] = u;
    parent[new_leaf] = mid;
    
    in_tree[mid] = true;
    in_tree[new_leaf] = true;
    
    sz[new_leaf] = 1;
    sz[mid] = sz[v] + 1 + 1; // v + mid + new_leaf(will be added via update)
    // Actually sz[mid] = sz[v] + 2 (itself + new_leaf)
    // Wait, sz[v] is already correct.
    // sz[mid] = sz[v] + 1 (itself).
    // Then we add new_leaf which is +1. So sz[mid] += 1.
    // Total increase to ancestors of u is 2 (mid and new_leaf).
    
    sz[mid] = sz[v] + 1; 
    update_size_up(u, 1); // mid added
    
    sz[new_leaf] = 1;
    update_size_up(mid, 1); // new_leaf added
}

void insert_node(int u, int curr);

void solve_lights(int u, int curr, int excluded) {
    vector<int> candidates;
    for (int v : adj[curr]) {
        if (v != parent[curr] && v != excluded) {
            candidates.push_back(v);
        }
    }
    
    while (!candidates.empty()) {
        if (candidates.size() == 1) {
            int v = candidates[0];
            vector<int> path;
            get_heavy_path(v, curr, path);
            int leaf = path.back();
            int res = query(curr, leaf, u);
            
            if (res == curr) {
                break;
            } else if (res == leaf) {
                 add_edge(leaf, u);
                 in_tree[u] = true;
                 return;
            } else if (in_tree[res]) {
                insert_node(u, res);
                return;
            } else {
                vector<int> full_path;
                full_path.push_back(curr);
                full_path.insert(full_path.end(), path.begin(), path.end());
                
                int L = 0, R = full_path.size() - 1;
                while (L + 1 < R) {
                    int mid = (L + R) / 2;
                    int val = query(full_path[mid], full_path[R], res);
                    if (val == res) L = mid;
                    else R = mid;
                }
                split_edge_and_add(full_path[L], full_path[R], res, u);
                return;
            }
        }
        
        int a = candidates.back(); candidates.pop_back();
        int b = candidates.back(); candidates.pop_back();
        
        vector<int> pathA, pathB;
        get_heavy_path(a, curr, pathA);
        get_heavy_path(b, curr, pathB);
        int leafA = pathA.back();
        int leafB = pathB.back();
        
        int res = query(leafA, leafB, u);
        
        if (res == curr) continue;
        
        bool inA = false;
        for(int x : pathA) if(x == res) inA = true;
        if (inA) { insert_node(u, res); return; }
        
        bool inB = false;
        for(int x : pathB) if(x == res) inB = true;
        if (inB) { insert_node(u, res); return; }
        
        int check = query(curr, leafA, res);
        if (check == res) {
             vector<int> full_path;
             full_path.push_back(curr);
             full_path.insert(full_path.end(), pathA.begin(), pathA.end());
             int L = 0, R = full_path.size() - 1;
             while (L + 1 < R) {
                 int mid = (L + R) / 2;
                 int val = query(full_path[mid], full_path[R], res);
                 if (val == res) L = mid;
                 else R = mid;
             }
             split_edge_and_add(full_path[L], full_path[R], res, u);
             return;
        } else {
             vector<int> full_path;
             full_path.push_back(curr);
             full_path.insert(full_path.end(), pathB.begin(), pathB.end());
             int L = 0, R = full_path.size() - 1;
             while (L + 1 < R) {
                 int mid = (L + R) / 2;
                 int val = query(full_path[mid], full_path[R], res);
                 if (val == res) L = mid;
                 else R = mid;
             }
             split_edge_and_add(full_path[L], full_path[R], res, u);
             return;
        }
    }
    
    add_edge(curr, u);
    in_tree[u] = true;
}

void insert_node(int u, int curr) {
    int h = get_heavy(curr, parent[curr]);
    if (h == -1) {
        add_edge(curr, u);
        in_tree[u] = true;
        return;
    }
    
    vector<int> path;
    get_heavy_path(h, curr, path);
    int leaf = path.back();
    
    int res = query(curr, leaf, u);
    
    if (res == curr) {
        solve_lights(u, curr, h);
    } else if (res == leaf) {
        add_edge(leaf, u);
        in_tree[u] = true;
    } else if (in_tree[res]) {
        int next_on_path = -1;
        for (size_t i = 0; i < path.size(); ++i) {
            if (path[i] == res && i + 1 < path.size()) {
                next_on_path = path[i+1];
                break;
            }
        }
        solve_lights(u, res, next_on_path);
    } else {
        vector<int> full_path;
        full_path.push_back(curr);
        full_path.insert(full_path.end(), path.begin(), path.end());
        int L = 0, R = full_path.size() - 1;
        while (L + 1 < R) {
             int mid = (L + R) / 2;
             int val = query(full_path[mid], full_path[R], res);
             if (val == res) L = mid;
             else R = mid;
        }
        split_edge_and_add(full_path[L], full_path[R], res, u);
    }
}

int main() {
    srand(12345);
    if (scanf("%d", &N) != 1) return 0;
    
    vector<int> p(N - 1);
    for (int i = 0; i < N - 1; ++i) p[i] = i + 2;
    random_shuffle(p.begin(), p.end());
    
    in_tree.assign(N + 1, false);
    in_tree[1] = true;
    parent[1] = 0;
    sz[1] = 1;
    
    for (int u : p) {
        if (!in_tree[u]) {
            insert_node(u, 1);
        }
    }
    
    cout << "1";
    for (int i = 1; i <= N; ++i) {
        for (int v : adj[i]) {
            if (i < v) {
                cout << " " << i << " " << v;
            }
        }
    }
    cout << endl;
    
    return 0;
}