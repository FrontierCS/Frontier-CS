#include <bits/stdc++.h>
using namespace std;

int get_bitlen(int x) {
    if (x == 0) return 0;
    return 32 - __builtin_clz(x);
}

int n_nodes;
vector<pair<int, int>> adj[105];
map<tuple<int, int, int>, int> memo;
int end_node = 2;

int get_node(int a, int b, int len) {
    if (a > b) return -1;
    if (len == 0) {
        return (a <= 0 && 0 <= b) ? end_node : -1;
    }
    tuple<int, int, int> key = make_tuple(len, a, b);
    if (memo.count(key)) {
        return memo[key];
    }
    int curr = ++n_nodes;
    int mid = 1 << (len - 1);
    // left v=0
    int la = max(a, 0);
    int lb = min(b, mid - 1);
    if (la <= lb) {
        int lsub = get_node(la, lb, len - 1);
        if (lsub != -1) {
            adj[curr].emplace_back(lsub, 0);
        }
    }
    // right v=1
    int ra = max(a - mid, 0);
    int rb = min(b - mid, mid - 1);
    if (ra <= rb) {
        int rsub = get_node(ra, rb, len - 1);
        if (rsub != -1) {
            adj[curr].emplace_back(rsub, 1);
        }
    }
    memo[key] = curr;
    return curr;
}

int main() {
    int L, R;
    cin >> L >> R;
    int mind = get_bitlen(L);
    int maxd = get_bitlen(R);
    n_nodes = 2; // 1: start, 2: end
    memo.clear();
    for (int i = 1; i <= 104; i++) adj[i].clear();
    for (int d = mind; d <= maxd; d++) {
        long long base = 1LL << (d - 1);
        long long glow = max((long long)L, base);
        long long ghigh = min((long long)R, base * 2 - 1);
        if (glow > ghigh) continue;
        int sa = (int)(glow - base);
        int sb = (int)(ghigh - base);
        int slen = d - 1;
        int sub = get_node(sa, sb, slen);
        if (sub != -1) {
            adj[1].emplace_back(sub, 1);
        }
    }
    int n = n_nodes;
    cout << n << '\n';
    for (int i = 1; i <= n; i++) {
        int k = adj[i].size();
        cout << k;
        for (auto p : adj[i]) {
            cout << " " << p.first << " " << p.second;
        }
        cout << '\n';
    }
    return 0;
}