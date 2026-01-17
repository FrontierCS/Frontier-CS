#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <map>

using namespace std;

int n, m;
vector<int> initial_colors;
vector<int> target_colors;
vector<vector<int>> adj;
vector<vector<int>> history;

void record_step(const vector<int>& current) {
    history.push_back(current);
}

// Applies a transformation where each node i chooses neighbor choice[i]
void apply_step(const vector<int>& choice, vector<int>& current_colors) {
    vector<int> next_colors(n);
    for (int i = 0; i < n; ++i) {
        int neighbor = choice[i];
        next_colors[i] = current_colors[neighbor];
    }
    current_colors = next_colors;
    record_step(current_colors);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    initial_colors.resize(n);
    for (int i = 0; i < n; ++i) cin >> initial_colors[i];
    target_colors.resize(n);
    for (int i = 0; i < n; ++i) cin >> target_colors[i];

    adj.resize(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    if (initial_colors == target_colors) {
        cout << 0 << "\n";
        cout << target_colors[0];
        for(int i=1; i<n; ++i) cout << " " << target_colors[i];
        cout << "\n";
        return 0;
    }

    vector<int> current_colors = initial_colors;

    // 1. Establish initial 0-1 edge
    int start_0 = -1, start_1 = -1;
    
    queue<int> q;
    vector<int> dist(n, -1);
    vector<int> parent(n, -1);
    for(int i=0; i<n; ++i) {
        if(current_colors[i] == 0) {
            q.push(i);
            dist[i] = 0;
        }
    }
    
    int found_1 = -1;
    while(!q.empty()){
        int u = q.front();
        q.pop();
        if(current_colors[u] == 1){
            found_1 = u;
            break;
        }
        for(int v : adj[u]){
            if(dist[v] == -1){
                dist[v] = dist[u] + 1;
                parent[v] = u;
                q.push(v);
            }
        }
    }

    vector<int> path;
    int curr = found_1;
    while(curr != -1 && current_colors[curr] != 0){
        path.push_back(curr);
        curr = parent[curr];
    }
    if (curr != -1) path.push_back(curr);
    reverse(path.begin(), path.end());

    for(size_t i = 0; i < path.size() - 2; ++i) {
        int u = path[i];
        int v = path[i+1];
        vector<int> choice(n);
        for(int j=0; j<n; ++j) choice[j] = j;
        choice[v] = u;
        apply_step(choice, current_colors);
    }
    
    int u_int = path[path.size()-2];
    int v_int = path.back();

    // 2. Build Spanning Tree and Order
    vector<bool> in_tree(n, false);
    vector<vector<int>> tree_adj(n);
    vector<int> bfs_q;
    bfs_q.push_back(u_int);
    in_tree[u_int] = true;
    if (!in_tree[v_int]) {
        in_tree[v_int] = true;
        tree_adj[u_int].push_back(v_int);
        tree_adj[v_int].push_back(u_int);
        bfs_q.push_back(v_int);
    }

    int head = 0;
    while(head < (int)bfs_q.size()){
        int u = bfs_q[head++];
        for(int v : adj[u]){
            if(!in_tree[v]){
                in_tree[v] = true;
                tree_adj[u].push_back(v);
                tree_adj[v].push_back(u);
                bfs_q.push_back(v);
            }
        }
    }

    vector<int> order;
    for(int i = bfs_q.size() - 1; i >= 0; --i) {
        order.push_back(bfs_q[i]);
    }

    vector<bool> active(n, true);

    for(int target_node : order) {
        if(!active[target_node]) continue;

        int active_cnt = 0;
        int other = -1;
        for(int i=0; i<n; ++i) if(active[i]) { active_cnt++; if(i!=target_node) other=i; }
        
        if(active_cnt <= 2) {
            if(active_cnt == 2) {
                int cur_t = current_colors[target_node];
                int cur_o = current_colors[other];
                int want_t = target_colors[target_node];
                int want_o = target_colors[other];
                
                if(cur_t == want_t && cur_o == want_o) {
                } else if(cur_t == want_o && cur_o == want_t) {
                    vector<int> choice(n);
                    for(int i=0; i<n; ++i) choice[i] = i;
                    choice[target_node] = other;
                    choice[other] = target_node;
                    apply_step(choice, current_colors);
                } else {
                    if(want_t == want_o) {
                        int src = (cur_t == want_t) ? target_node : other;
                        int dst = (src == target_node) ? other : target_node;
                        vector<int> choice(n);
                        for(int i=0; i<n; ++i) choice[i] = i;
                        choice[dst] = src;
                        apply_step(choice, current_colors);
                    }
                }
            }
            break;
        }

        queue<int> q_path;
        vector<int> path_parent(n, -2);
        q_path.push(u_int);
        q_path.push(v_int);
        path_parent[u_int] = -1;
        path_parent[v_int] = -1;
        
        bool found = false;
        int end_node = -1;
        
        if(u_int == target_node || v_int == target_node) {
            found = true;
            end_node = (u_int == target_node) ? u_int : v_int;
        }

        int head_q = 0;
        vector<int> q_vec; 
        if(!found) {
            q_vec.push_back(u_int);
            q_vec.push_back(v_int);
        }
        
        while(head_q < (int)q_vec.size() && !found) {
            int u = q_vec[head_q++];
            for(int v : tree_adj[u]) {
                if(active[v] && path_parent[v] == -2) {
                    path_parent[v] = u;
                    if(v == target_node) {
                        found = true;
                        end_node = v;
                        break;
                    }
                    q_vec.push_back(v);
                }
            }
        }
        
        vector<int> nav_path;
        curr = end_node;
        while(curr != -1 && curr != u_int && curr != v_int) {
            nav_path.push_back(curr);
            curr = path_parent[curr];
        }
        nav_path.push_back(curr);
        reverse(nav_path.begin(), nav_path.end());

        for(size_t i = 0; i < nav_path.size(); ++i) {
            int next_node = nav_path[i];
            if(next_node == u_int || next_node == v_int) continue;
            
            int root_node = -1, other_node = -1;
            bool u_is_root = false;
            for(int nb : tree_adj[u_int]) if(nb == next_node) u_is_root = true;
            
            if(u_is_root) {
                root_node = u_int; other_node = v_int;
            } else {
                root_node = v_int; other_node = u_int;
            }
            
            vector<int> choice1(n); for(int k=0; k<n; ++k) choice1[k]=k;
            choice1[next_node] = root_node;
            apply_step(choice1, current_colors);
            
            vector<int> choice2(n); for(int k=0; k<n; ++k) choice2[k]=k;
            choice2[root_node] = other_node;
            apply_step(choice2, current_colors);
            
            v_int = root_node;
            u_int = next_node;
        }
        
        int t_node = target_node;
        int p_node = (u_int == t_node) ? v_int : u_int;
        
        if(current_colors[t_node] != target_colors[t_node]) {
            if(current_colors[p_node] == target_colors[t_node]) {
                vector<int> choice(n); for(int k=0; k<n; ++k) choice[k]=k;
                choice[t_node] = p_node;
                choice[p_node] = t_node;
                apply_step(choice, current_colors);
            }
        }
        
        active[t_node] = false;
        
        int next_hop = -1;
        for(int nb : tree_adj[p_node]) {
            if(active[nb]) {
                next_hop = nb;
                break;
            }
        }
        
        if(next_hop != -1) {
            vector<int> choice1(n); for(int k=0; k<n; ++k) choice1[k]=k;
            choice1[next_hop] = p_node;
            apply_step(choice1, current_colors);
            
            vector<int> choice2(n); for(int k=0; k<n; ++k) choice2[k]=k;
            choice2[p_node] = t_node;
            apply_step(choice2, current_colors);
            
            u_int = next_hop;
            v_int = p_node;
        }
    }

    cout << history.size() << "\n";
    cout << initial_colors[0];
    for(int i=1; i<n; ++i) cout << " " << initial_colors[i];
    cout << "\n";
    for(const auto& state : history) {
        cout << state[0];
        for(int i=1; i<n; ++i) cout << " " << state[i];
        cout << "\n";
    }

    return 0;
}