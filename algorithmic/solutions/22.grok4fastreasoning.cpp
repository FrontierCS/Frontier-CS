#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    cin >> N;
    vector<int> parent(N + 1, 0);
    vector<vector<int>> children(N + 1);
    for (int i = 2; i <= N; ++i) {
        int p;
        cin >> p;
        parent[i] = p;
        children[p].push_back(i);
    }
    
    vector<int> leaves;
    for (int i = 2; i <= N; ++i) {
        if (children[i].empty()) {
            leaves.push_back(i);
        }
    }
    int k = leaves.size();
    
    vector<int> bag_for_node(N + 1, 0);
    vector<vector<int>> X;
    X.resize(4 * N + 10); // safe size
    int cur_id = 1;
    
    // B_leaf
    vector<int> B_leaf(k);
    for (int i = 0; i < k; ++i) {
        int v = leaves[i];
        int p = parent[v];
        B_leaf[i] = cur_id;
        X[cur_id] = {p, v};
        bag_for_node[v] = cur_id;
        ++cur_id;
    }
    
    // internal edges
    vector<pair<int, int>> int_pairs;
    function<void(int, int)> dfs_count = [&](int u, int pr) {
        for (int c : children[u]) {
            if (c != pr) {
                dfs_count(c, u);
                if (!children[c].empty()) {
                    int_pairs.emplace_back(u, c);
                }
            }
        }
    };
    dfs_count(1, 0);
    int num_int = int_pairs.size();
    vector<int> B_int(num_int);
    for (int i = 0; i < num_int; ++i) {
        auto [u, v] = int_pairs[i];
        B_int[i] = cur_id;
        X[cur_id] = {u, v};
        bag_for_node[v] = cur_id;
        ++cur_id;
    }
    
    // H for leaves
    vector<int> HH(k);
    for (int i = 0; i < k; ++i) {
        int v = leaves[i];
        int p = parent[v];
        HH[i] = cur_id;
        X[cur_id] = {v, p};
        ++cur_id;
    }
    
    // M left and right
    vector<int> Mleft(k), Mright(k);
    for (int i = 0; i < k; ++i) {
        int v1 = leaves[i];
        int v2 = leaves[(i + 1) % k];
        Mleft[i] = cur_id;
        X[cur_id] = {v1, v2};
        ++cur_id;
        Mright[i] = cur_id;
        X[cur_id] = {v1, v2};
        ++cur_id;
    }
    
    int total_K = cur_id - 1;
    
    // tree edges
    vector<pair<int, int>> tree_ed;
    
    // leaf locals
    for (int i = 0; i < k; ++i) {
        int hi = HH[i];
        int bi = B_leaf[i];
        tree_ed.emplace_back(hi, bi);
        
        int pre = (i + k - 1) % k;
        int m_pr = Mright[pre];
        tree_ed.emplace_back(hi, m_pr);
        
        int m_nl = Mleft[i];
        tree_ed.emplace_back(hi, m_nl);
    }
    
    // root children path
    vector<int> rc = children[1];
    sort(rc.begin(), rc.end());
    for (size_t j = 0; j + 1 < rc.size(); ++j) {
        int c1 = rc[j];
        int id1 = bag_for_node[c1];
        int c2 = rc[j + 1];
        int id2 = bag_for_node[c2];
        tree_ed.emplace_back(id1, id2);
    }
    
    // down connections
    function<void(int, int)> connect_d = [&](int u, int pr) {
        int bu = (u == 1 ? 0 : bag_for_node[u]);
        for (int c : children[u]) {
            if (c != pr) {
                int bc = bag_for_node[c];
                if (u != 1) {
                    tree_ed.emplace_back(bu, bc);
                }
                connect_d(c, u);
            }
        }
    };
    connect_d(1, 0);
    
    // output
    cout << total_K << '\n';
    for (int i = 1; i <= total_K; ++i) {
        vector<int>& s = X[i];
        cout << s.size();
        for (int x : s) {
            cout << ' ' << x;
        }
        cout << '\n';
    }
    for (auto [a, b] : tree_ed) {
        cout << a << ' ' << b << '\n';
    }
    
    return 0;
}