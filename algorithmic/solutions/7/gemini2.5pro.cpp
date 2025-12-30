#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <map>

#if defined(_MSC_VER)
#include <intrin.h>
#endif

using namespace std;

vector<pair<int, int>> adj[102];
int nextNode = 2;
map<int, int> F_nodes;
const int END_NODE_PLACEHOLDER = 101; 

int get_F(int i);

void solve_ge_suffix(int u, int val, int k) {
    int curr = u;
    for (int i = k - 1; i >= 0; --i) {
        int bit = (val >> i) & 1;
        if (bit == 0) {
            adj[curr].push_back({get_F(i), 1});
            int next_v = (i > 0) ? nextNode++ : END_NODE_PLACEHOLDER;
            adj[curr].push_back({next_v, 0});
            curr = next_v;
        } else {
            int next_v = (i > 0) ? nextNode++ : END_NODE_PLACEHOLDER;
            adj[curr].push_back({next_v, 1});
            curr = next_v;
        }
    }
}

void solve_le_suffix(int u, int val, int k) {
    int curr = u;
    for (int i = k - 1; i >= 0; --i) {
        int bit = (val >> i) & 1;
        if (bit == 1) {
            adj[curr].push_back({get_F(i), 0});
            int next_v = (i > 0) ? nextNode++ : END_NODE_PLACEHOLDER;
            adj[curr].push_back({next_v, 1});
            curr = next_v;
        } else {
            int next_v = (i > 0) ? nextNode++ : END_NODE_PLACEHOLDER;
            adj[curr].push_back({next_v, 0});
            curr = next_v;
        }
    }
}

void solve(int l, int r, int k) {
    if (l == r) {
        int curr = 1;
        for (int i = k - 1; i >= 0; --i) {
            int bit = (l >> i) & 1;
            int next_v = (i > 0) ? nextNode++ : END_NODE_PLACEHOLDER;
            adj[curr].push_back({next_v, bit});
            curr = next_v;
        }
        return;
    }
    
    int p = -1;
    for (int i = k - 1; i >= 0; --i) {
        if (((l >> i) & 1) != ((r >> i) & 1)) {
            p = i;
            break;
        }
    }

    int curr = 1;
    for (int i = k - 1; i > p; --i) {
        int bit = (l >> i) & 1;
        int next_v = nextNode++;
        adj[curr].push_back({next_v, bit});
        curr = next_v;
    }

    int l_suf = l & ((1 << p) - 1);
    int r_suf = r & ((1 << p) - 1);

    int vL = nextNode++;
    adj[curr].push_back({vL, 0});
    solve_ge_suffix(vL, l_suf, p);

    int vR = nextNode++;
    adj[curr].push_back({vR, 1});
    solve_le_suffix(vR, r_suf, p);
}


void solve_ge_main(int val, int k) {
    int curr = 1;
    if (k > 0) {
        int next_v = (k > 1) ? nextNode++ : END_NODE_PLACEHOLDER;
        adj[curr].push_back({next_v, 1});
        curr = next_v;
    } else { 
        return;
    }

    for (int i = k - 2; i >= 0; --i) {
        int bit = (val >> i) & 1;
        if (bit == 0) {
            adj[curr].push_back({get_F(i), 1});
            int next_v = (i > 0) ? nextNode++ : END_NODE_PLACEHOLDER;
            adj[curr].push_back({next_v, 0});
            curr = next_v;
        } else {
            int next_v = (i > 0) ? nextNode++ : END_NODE_PLACEHOLDER;
            adj[curr].push_back({next_v, 1});
            curr = next_v;
        }
    }
}


void solve_le_main(int val, int k) {
    int curr = 1;
    if (k > 0) {
        int next_v = (k > 1) ? nextNode++ : END_NODE_PLACEHOLDER;
        adj[curr].push_back({next_v, 1});
        curr = next_v;
    } else {
        return;
    }
    
    for (int i = k - 2; i >= 0; --i) {
        int bit = (val >> i) & 1;
        if (bit == 1) {
            adj[curr].push_back({get_F(i), 0});
            int next_v = (i > 0) ? nextNode++ : END_NODE_PLACEHOLDER;
            adj[curr].push_back({next_v, 1});
            curr = next_v;
        } else {
            int next_v = (i > 0) ? nextNode++ : END_NODE_PLACEHOLDER;
            adj[curr].push_back({next_v, 0});
            curr = next_v;
        }
    }
}


int get_F(int i) {
    if (i == 0) return END_NODE_PLACEHOLDER;
    if (F_nodes.count(i)) return F_nodes[i];
    
    int u = F_nodes[i] = nextNode++;
    int v = get_F(i - 1);
    adj[u].push_back({v, 0});
    adj[u].push_back({v, 1});
    return u;
}

int bit_length(unsigned int n) {
    if (n == 0) return 0;
#if defined(_MSC_VER)
    unsigned long index;
    _BitScanReverse(&index, n);
    return index + 1;
#else
    return 32 - __builtin_clz(n);
#endif
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int L, R;
    cin >> L >> R;
    
    int lenL = bit_length(L);
    int lenR = bit_length(R);

    if (lenL == lenR) {
        solve(L, R, lenL);
    } else {
        solve_ge_main(L, lenL);
        for (int k = lenL + 1; k < lenR; ++k) {
            adj[1].push_back({get_F(k - 1), 1});
        }
        solve_le_main(R, lenR);
    }

    int end_node_id = nextNode;
    for (int i = 1; i < nextNode; ++i) {
        for (auto& edge : adj[i]) {
            if (edge.first == END_NODE_PLACEHOLDER) {
                edge.first = end_node_id;
            }
        }
    }
    
    cout << end_node_id << endl;
    for (int i = 1; i <= end_node_id; ++i) {
        cout << adj[i].size();
        for (const auto& edge : adj[i]) {
            cout << " " << edge.first << " " << edge.second;
        }
        cout << endl;
    }

    return 0;
}