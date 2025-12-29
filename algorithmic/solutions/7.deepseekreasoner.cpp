#include <bits/stdc++.h>
using namespace std;

using ll = long long;

ll L, R;
int n; // bit length of R

vector<vector<pair<int, int>>> edges; // edges[node] = list of (target, weight)
int n_nodes;
map<pair<ll, int>, int> node_id;

int get_node(ll val, int len) {
    auto key = make_pair(val, len);
    if (node_id.count(key)) return node_id[key];
    int id = ++n_nodes;
    node_id[key] = id;
    edges.emplace_back(); // placeholder for this node's edges, index = id
    // for b = 0 and 1
    for (int b = 0; b <= 1; ++b) {
        ll new_val = val * 2 + b;
        int new_len = len + 1;
        // compute the range of numbers with prefix new_val
        ll new_min = max(L, new_val);
        int k = n - new_len;
        ll max_ext = (k >= 0) ? (new_val * (1LL << k) + ((1LL << k) - 1)) : new_val;
        ll new_max = min(R, max_ext);
        if (new_min > new_max) continue; // no numbers
        // if new_val itself is a valid number, add edge to end
        if (new_val >= L && new_val <= R) {
            edges[id].emplace_back(2, b);
        }
        // if there exist longer numbers (i.e., numbers with prefix new_val and length > new_len)
        if (new_max > new_val) {
            int child = get_node(new_val, new_len);
            edges[id].emplace_back(child, b);
        }
    }
    return id;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> L >> R;
    // compute n = bit length of R
    n = 0;
    while ((1LL << n) <= R) ++n;
    // initialize nodes: 1 = start, 2 = end
    n_nodes = 2;
    edges.resize(3); // indices 1 and 2 used
    node_id.clear();
    // handle first bit from start
    // if 1 is in [L,R], add edge from start to end with weight 1
    if (1 >= L && 1 <= R) {
        edges[1].emplace_back(2, 1);
    }
    // check if there are numbers longer than 1 starting with 1
    ll min_val = max(L, 1LL);
    int k = n - 1;
    ll max_ext = 1 * (1LL << k) + ((1LL << k) - 1);
    ll max_val = min(R, max_ext);
    if (max_val > 1) {
        int child = get_node(1, 1);
        edges[1].emplace_back(child, 1);
    }
    // output
    cout << n_nodes << "\n";
    for (int i = 1; i <= n_nodes; ++i) {
        cout << edges[i].size();
        for (auto [to, w] : edges[i]) {
            cout << " " << to << " " << w;
        }
        cout << "\n";
    }
    return 0;
}