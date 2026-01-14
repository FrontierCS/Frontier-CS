#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <map>
#include <tuple>

using namespace std;

using ll = long long;

struct Edge {
    int to;
    int weight;
};

vector<vector<Edge>> adj;
int n_nodes;

int newNode() {
    n_nodes++;
    adj.resize(n_nodes + 1);
    return n_nodes;
}

map<tuple<int, ll, ll>, int> memo;

int gen(int len, ll l, ll r) {
    if (l > r) {
        return 2;
    }
    if (len == 0) {
        return 2;
    }
    if (memo.count({len, l, r})) {
        return memo.at({len, l, r});
    }

    int u = newNode();
    memo[{len, l, r}] = u;

    ll p_val = 1LL << (len - 1);

    if (r < p_val) { // All numbers' MSB is 0
        int next_node = gen(len - 1, l, r);
        adj[u].push_back({next_node, 0});
    } else if (l >= p_val) { // All numbers' MSB is 1
        int next_node = gen(len - 1, l - p_val, r - p_val);
        adj[u].push_back({next_node, 1});
    } else { // Divergence
        // Range [l, p_val - 1] starts with 0
        int next_l = gen(len - 1, l, p_val - 1);
        adj[u].push_back({next_l, 0});

        // Range [p_val, r] starts with 1
        int next_r = gen(len - 1, 0, r - p_val);
        adj[u].push_back({next_r, 1});
    }
    return u;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    ll L, R;
    cin >> L >> R;

    n_nodes = 2; // 1: start, 2: end
    adj.resize(n_nodes + 1);

    if (L == 1) {
        adj[1].push_back({2, 1});
        L = 2;
    }

    if (L <= R) {
        int lenL = floor(log2(L)) + 1;
        int lenR = floor(log2(R)) + 1;

        for (int k = lenL; k <= lenR; ++k) {
            ll low_k = (k == lenL) ? L : (1LL << (k - 1));
            ll high_k = (k == lenR) ? R : (1LL << k) - 1;

            if (low_k > high_k) continue;

            ll suffix_l = low_k - (1LL << (k - 1));
            ll suffix_r = high_k - (1LL << (k - 1));

            int suffix_start_node = gen(k - 1, suffix_l, suffix_r);
            adj[1].push_back({suffix_start_node, 1});
        }
    }

    cout << n_nodes << endl;
    for (int i = 1; i <= n_nodes; ++i) {
        cout << adj[i].size();
        for (const auto& edge : adj[i]) {
            cout << " " << edge.to << " " << edge.weight;
        }
        cout << endl;
    }

    return 0;
}