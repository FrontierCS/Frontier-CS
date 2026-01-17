#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <random>

using namespace std;

int N;
vector<int> adj[1005];
int parent[1005];
bool active[1005];
int sub_sz[1005];
int tin[1005], tout[1005];
int timer;
map<vector<int>, int> cache_query;

void add_edge(int u, int v) {
    adj[u].push_back(v);
    adj[v].push_back(u);
}

void remove_edge(int u, int v) {
    auto it = find(adj[u].begin(), adj[u].end(), v);
    if (it != adj[u].end()) adj[u].erase(it);
    it = find(adj[v].begin(), adj[v].end(), u);
    if (it != adj[v].end()) adj[v].erase(it);
}

int query(int u, int v, int w) {
    if (u > v) swap(u, v);
    if (v > w) swap(v, w);
    if (u > v) swap(u, v);
    vector<int> key = {u, v, w};
    if (cache_query.count(key)) return cache_query[key];
    
    cout << "0 " << u << " " << v << " " << w << endl;
    int res;
    cin >> res;
    return cache_query[key] = res;
}

void dfs_sz(int u, int p) {
    tin[u] = ++timer;
    sub_sz[u] = 1;
    parent[u] = p;
    for (int v : adj[u]) {
        if (v != p) {
            dfs_sz(v, u);
            sub_sz[u] += sub_sz[v];
        }
    }
    tout[u] = timer;
}

bool is_ancestor(int u, int v) { // is u ancestor of v
    return tin[u] <= tin[v] && tout[u] >= tout[v];
}

void split_edge(int u, int v, int mid) {
    remove_edge(u, v);
    add_edge(u, mid);
    add_edge(mid, v);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N)) return 0;
    
    vector<int> p(N);
    for (int i = 0; i < N; ++i) p[i] = i + 1;
    
    // Random shuffle to ensure O(N log N) behavior on average
    mt19937 rng(1337);
    shuffle(p.begin(), p.end(), rng);
    
    // Initial tree: just the first node
    active[p[0]] = true;
    int root = p[0];
    
    for (int i = 1; i < N; ++i) {
        int u = p[i];
        if (active[u]) continue;
        
        int curr = root;
        while (true) {
            timer = 0;
            dfs_sz(root, 0); // Recompute sizes and ancestry info
            
            int heavy = -1;
            vector<pair<int, int>> lights;
            
            for (int v : adj[curr]) {
                if (v == parent[curr]) continue;
                if (sub_sz[v] * 2 > sub_sz[curr]) {
                    heavy = v;
                } else {
                    lights.push_back({sub_sz[v], v});
                }
            }
            // Sort light children by size descending for efficient elimination
            sort(lights.rbegin(), lights.rend());
            
            // Check heavy child first
            if (heavy != -1) {
                int w = query(curr, heavy, u);
                if (w == heavy || is_ancestor(heavy, w)) {
                    curr = w;
                    continue;
                }
                if (w != curr) {
                    split_edge(curr, heavy, w);
                    active[w] = true;
                    if (w == u) break;
                    curr = w;
                    continue;
                }
                // if w == curr, u is not in heavy branch, proceed to lights
            }
            
            bool moved = false;
            vector<int> l_nodes;
            for(auto pp : lights) l_nodes.push_back(pp.second);
            
            while (l_nodes.size() >= 2) {
                int a = l_nodes[0];
                int b = l_nodes[1];
                l_nodes.erase(l_nodes.begin());
                l_nodes.erase(l_nodes.begin());
                
                int w = query(a, b, u);
                if (w == curr) continue; // u is not in subtree a or b
                
                if (w == a || is_ancestor(a, w)) {
                    curr = w; moved = true; break;
                }
                if (w == b || is_ancestor(b, w)) {
                    curr = w; moved = true; break;
                }
                
                // w is new or intermediate on path a-b
                // Determine side using one more query
                int side = query(curr, a, w);
                if (side == w) { // on curr-a
                    split_edge(curr, a, w);
                } else {
                    split_edge(curr, b, w);
                }
                active[w] = true;
                if (w == u) { moved = true; break; }
                curr = w; moved = true; break;
            }
            
            if (moved) {
                if (active[u]) break; 
                continue;
            }
            
            if (l_nodes.size() == 1) {
                int a = l_nodes[0];
                int w = query(curr, a, u);
                if (w == curr) {
                    add_edge(curr, u);
                    active[u] = true;
                    break;
                }
                if (w == a || is_ancestor(a, w)) {
                    curr = w;
                    continue;
                }
                split_edge(curr, a, w);
                active[w] = true;
                if (w == u) break;
                curr = w;
                continue;
            }
            
            // No candidates
            add_edge(curr, u);
            active[u] = true;
            break;
        }
    }
    
    cout << "1";
    vector<pair<int, int>> edges;
    for (int i = 1; i <= N; ++i) {
        for (int v : adj[i]) {
            if (i < v) edges.push_back({i, v});
        }
    }
    for (auto e : edges) cout << " " << e.first << " " << e.second;
    cout << endl;
    
    return 0;
}