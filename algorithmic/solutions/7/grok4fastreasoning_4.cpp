#include <bits/stdc++.h>
using namespace std;

vector<int> get_bits(long long x) {
    vector<int> res;
    if (x == 0) return res;
    while (x > 0) {
        res.push_back(x % 2);
        x /= 2;
    }
    reverse(res.begin(), res.end());
    return res;
}

int main() {
    long long L, R;
    cin >> L >> R;
    int node_cnt = 1; // 1 is root
    int endn = ++node_cnt; // 2 is end
    vector<int> fulls(21, -1);
    fulls[0] = endn;
    function<int(int)> get_full = [&](int rem) -> int {
        if (fulls[rem] != -1) return fulls[rem];
        if (rem == 0) return fulls[0];
        int nd = ++node_cnt;
        int nxt = get_full(rem - 1);
        // We will add edges later? No, add here.
        // But since vector not yet, wait, g not defined.
        // Wait, move g inside.
        return fulls[rem] = nd; // Temporarily, add edges after all? No.
        // Problem: g not defined yet.
    };
    // Better define g now.
    vector<vector<pair<int, int>>> g(105);
    // Now redefine get_full with g.
    auto get_full_lambda = [&](auto&& self, int rem) -> int {
        if (fulls[rem] != -1) return fulls[rem];
        if (rem == 0) return fulls[0];
        int nd = ++node_cnt;
        int nxt = self(self, rem - 1);
        g[nd].emplace_back(nxt, 0);
        g[nd].emplace_back(nxt, 1);
        return fulls[rem] = nd;
    };
    vector<pair<long long, int>> blocks;
    long long cur = L;
    while (cur <= R) {
        long long remn = R - cur + 1;
        int k = 0;
        while ((1LL << (k + 1)) <= remn && (cur % (1LL << (k + 1))) == 0) ++k;
        blocks.emplace_back(cur, k);
        cur += (1LL << k);
    }
    for (auto [st, kk] : blocks) {
        long long pre = st >> kk;
        vector<int> bits = get_bits(pre);
        int m = bits.size();
        int target = get_full_lambda(get_full_lambda, kk);
        int current = 1;
        for (int i = 0; i < m; ++i) {
            int bitv = bits[i];
            int nxt;
            if (i == m - 1) {
                nxt = target;
            } else {
                nxt = ++node_cnt;
            }
            // Check if edge already exists
            bool exists = false;
            for (auto& p : g[current]) {
                if (p.first == nxt && p.second == bitv) {
                    exists = true;
                    break;
                }
            }
            if (!exists) {
                g[current].emplace_back(nxt, bitv);
            }
            current = nxt;
        }
    }
    int n = node_cnt;
    cout << n << endl;
    for (int i = 1; i <= n; ++i) {
        int k = g[i].size();
        cout << k;
        for (auto& p : g[i]) {
            cout << " " << p.first << " " << p.second;
        }
        cout << endl;
    }
    return 0;
}