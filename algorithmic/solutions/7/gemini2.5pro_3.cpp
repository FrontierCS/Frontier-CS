#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <map>
#include <tuple>

using namespace std;

typedef long long ll;

int n = 0;
vector<pair<int, int>> adj[101];

int new_node() {
    return ++n;
}

int any_nodes[21];
map<tuple<ll, ll, int>, int> memo;

int get_len(ll val) {
    if (val == 0) return 1;
    if (val < 0) return 0; // Should not happen
    return 64 - __builtin_clzll(val);
}

int gen(ll l, ll r, int len, int end_node);

void build_chain(int start_node, ll val, int len, int end_node) {
    int curr = start_node;
    for (int i = len - 1; i > 0; --i) {
        int bit = (val >> i) & 1;
        int next_node = new_node();
        adj[curr].push_back({next_node, bit});
        curr = next_node;
    }
    if (len > 0) {
        int bit = val & 1;
        adj[curr].push_back({end_node, bit});
    } else { 
        // A direct connection from start_node to end_node would need a bit.
        // This case is handled by gen returning end_node for len=0,
        // so the caller connects to end_node.
    }
}

int gen(ll l, ll r, int len, int end_node) {
    if (len == 0) return end_node;
    if (l > r) return 0; // Sentinel for no path

    if (memo.count({l, r, len})) {
        return memo.at({l, r, len});
    }

    int start_node = new_node();
    memo[{l, r, len}] = start_node;

    if (l == 0 && r == (1LL << len) - 1) {
        if (len > 0) {
            adj[start_node].push_back({any_nodes[len - 1], 0});
            adj[start_node].push_back({any_nodes[len - 1], 1});
        }
        return start_node;
    }
    
    if (l == r) {
        build_chain(start_node, l, len, end_node);
        return start_node;
    }

    int msb_pos = -1;
    for (int i = len - 1; i >= 0; --i) {
        if (((l >> i) & 1) != ((r >> i) & 1)) {
            msb_pos = i;
            break;
        }
    }

    int curr = start_node;
    for (int i = len - 1; i > msb_pos; --i) {
        int bit = (l >> i) & 1;
        int next_node = new_node();
        adj[curr].push_back({next_node, bit});
        curr = next_node;
    }

    int len_suffix = msb_pos + 1;
    ll mask_suffix = (1LL << len_suffix) - 1;

    // Path for bit 0 at msb_pos
    ll l_for_0_path = l & mask_suffix;
    int child_for_0 = gen(l_for_0_path, mask_suffix, len_suffix, end_node);
    if (child_for_0 != 0) {
        adj[curr].push_back({child_for_0, 0});
    }

    // Path for bit 1 at msb_pos
    ll r_for_1_path = r & mask_suffix;
    int child_for_1 = gen(0, r_for_1_path, len_suffix, end_node);
    if (child_for_1 != 0) {
        adj[curr].push_back({child_for_1, 1});
    }

    return start_node;
}

void solve_range_fixed_len(ll l, ll r) {
    if (l > r) return;
    int d = get_len(l);
    if (l == 0) d = get_len(r); // should not happen with L>=1
    
    ll rem_l = l - (1LL << (d - 1));
    ll rem_r = r - (1LL << (d - 1));
    int u = gen(rem_l, rem_r, d - 1, 2);
    if (u != 0 && u != 2) {
        adj[1].push_back({u, 1});
    } else if (u == 2 && d == 1) { // Special case for number 1
        adj[1].push_back({2, 1});
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    ll L, R;
    cin >> L >> R;

    n = 2; // Start node 1, End node 2

    any_nodes[0] = 2;
    for (int i = 1; i <= 20; ++i) {
        any_nodes[i] = new_node();
    }
    for (int i = 1; i <= 20; ++i) {
        adj[any_nodes[i]].push_back({any_nodes[i - 1], 0});
        adj[any_nodes[i]].push_back({any_nodes[i - 1], 1});
    }
    
    int len_l = get_len(L);
    int len_r = get_len(R);
    
    if (len_l == len_r) {
        solve_range_fixed_len(L, R);
    } else {
        solve_range_fixed_len(L, (1LL << len_l) - 1);
        for (int d = len_l + 1; d < len_r; ++d) {
            solve_range_fixed_len(1LL << (d - 1), (1LL << d) - 1);
        }
        solve_range_fixed_len(1LL << (len_r - 1), R);
    }
    
    int final_n = n;
    if (final_n > 2) {
        // Swap node 2 and node final_n to make final_n the end node
        swap(adj[2], adj[final_n]);
        for(int i=1; i<=final_n; ++i) {
            for(auto& edge : adj[i]) {
                if(edge.first == 2) edge.first = final_n;
                else if (edge.first == final_n) edge.first = 2;
            }
        }
    }
    
    cout << final_n << "\n";
    for (int i = 1; i <= final_n; ++i) {
        sort(adj[i].begin(), adj[i].end());
        cout << adj[i].size();
        for (auto const& [neighbor, weight] : adj[i]) {
            cout << " " << neighbor << " " << weight;
        }
        cout << "\n";
    }

    return 0;
}