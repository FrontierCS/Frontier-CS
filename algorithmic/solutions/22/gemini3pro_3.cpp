#include <iostream>
#include <vector>
#include <algorithm>
#include <set>

using namespace std;

const int MAXN = 100005;
vector<int> adj[MAXN];
int L[MAXN], R[MAXN];
bool is_leaf[MAXN];

vector<vector<int>> all_bags;
vector<pair<int, int>> tree_edges;

void dfs_LR(int u) {
    if (adj[u].empty()) {
        is_leaf[u] = true;
        L[u] = R[u] = u;
    } else {
        is_leaf[u] = false;
        L[u] = MAXN;
        R[u] = -1;
        for (int v : adj[u]) {
            dfs_LR(v);
            L[u] = min(L[u], L[v]);
            R[u] = max(R[u], R[v]);
        }
    }
}

// Returns pair {first_bag_id, last_bag_id}
pair<int, int> solve(int u, int p) {
    if (is_leaf[u]) {
        vector<int> content;
        content.push_back(u);
        if (p != 0 && p != u) content.push_back(p);
        
        sort(content.begin(), content.end());
        content.erase(unique(content.begin(), content.end()), content.end());
        
        all_bags.push_back(content);
        int id = all_bags.size();
        return {id, id};
    }

    int m = adj[u].size();
    bool is_root = (u == 1);
    int extra_node = is_root ? L[u] : -1;

    // Process children
    vector<pair<int, int>> child_res(m);
    for (int i = 0; i < m; ++i) {
        child_res[i] = solve(adj[u][i], u);
    }

    // Create NodeBag_1
    vector<int> nb1_content;
    nb1_content.push_back(u);
    if (p != 0 && p != u) nb1_content.push_back(p);
    nb1_content.push_back(adj[u][0]);
    nb1_content.push_back(L[adj[u][0]]); 
    if (extra_node != -1) nb1_content.push_back(extra_node);

    sort(nb1_content.begin(), nb1_content.end());
    nb1_content.erase(unique(nb1_content.begin(), nb1_content.end()), nb1_content.end());

    all_bags.push_back(nb1_content);
    int node_bag_curr = all_bags.size();
    int first_bag_id = node_bag_curr;
    
    // Connect to f_1
    tree_edges.push_back({node_bag_curr, child_res[0].first});

    int prev_bag = node_bag_curr;

    for (int i = 0; i < m - 1; ++i) {
        // CycleBag_i
        // Connects R(c_i) and L(c_{i+1})
        int r_curr = R[adj[u][i]];
        int l_next = L[adj[u][i+1]];
        
        vector<int> cb_content;
        cb_content.push_back(u);
        if (p != 0 && p != u) cb_content.push_back(p);
        cb_content.push_back(r_curr);
        cb_content.push_back(l_next);
        if (extra_node != -1) cb_content.push_back(extra_node);
        
        sort(cb_content.begin(), cb_content.end());
        cb_content.erase(unique(cb_content.begin(), cb_content.end()), cb_content.end());

        all_bags.push_back(cb_content);
        int cycle_bag = all_bags.size();
        
        // Connect l_i (which is last of child i) to cycle bag
        tree_edges.push_back({child_res[i].second, cycle_bag});
        // Connect prev_bag to cycle bag
        tree_edges.push_back({prev_bag, cycle_bag});
        
        // NodeBag_{i+1}
        int c_next = adj[u][i+1];
        
        vector<int> nb_next_content;
        nb_next_content.push_back(u);
        if (p != 0 && p != u) nb_next_content.push_back(p);
        nb_next_content.push_back(c_next);
        nb_next_content.push_back(l_next);
        if (extra_node != -1) nb_next_content.push_back(extra_node);
        
        sort(nb_next_content.begin(), nb_next_content.end());
        nb_next_content.erase(unique(nb_next_content.begin(), nb_next_content.end()), nb_next_content.end());

        all_bags.push_back(nb_next_content);
        int node_bag_next = all_bags.size();
        
        // Connect cycle bag to new node bag
        tree_edges.push_back({cycle_bag, node_bag_next});
        // Connect new node bag to f_{i+1}
        tree_edges.push_back({node_bag_next, child_res[i+1].first});
        
        prev_bag = node_bag_next;
    }

    // TailBag
    int c_last = adj[u].back();
    int r_last = R[c_last];
    
    vector<int> tb_content;
    tb_content.push_back(u);
    if (p != 0 && p != u) tb_content.push_back(p);
    tb_content.push_back(c_last);
    tb_content.push_back(r_last);
    if (extra_node != -1) tb_content.push_back(extra_node);
    
    sort(tb_content.begin(), tb_content.end());
    tb_content.erase(unique(tb_content.begin(), tb_content.end()), tb_content.end());

    all_bags.push_back(tb_content);
    int tail_bag = all_bags.size();
    
    // Connect l_m to tail bag
    tree_edges.push_back({child_res.back().second, tail_bag});
    // Connect prev_bag to tail bag
    tree_edges.push_back({prev_bag, tail_bag});
    
    return {first_bag_id, tail_bag};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N;
    if (!(cin >> N)) return 0;

    for (int i = 0; i < N - 1; ++i) {
        int p;
        cin >> p;
        adj[p].push_back(i + 2);
    }
    
    dfs_LR(1);
    
    solve(1, 0);
    
    cout << all_bags.size() << "\n";
    for (const auto& bag : all_bags) {
        cout << bag.size();
        for (int x : bag) {
            cout << " " << x;
        }
        cout << "\n";
    }
    
    for (const auto& edge : tree_edges) {
        cout << edge.first << " " << edge.second << "\n";
    }

    return 0;
}