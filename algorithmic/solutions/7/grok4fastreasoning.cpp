#include <bits/stdc++.h>
using namespace std;

int main() {
    long long L, R;
    cin >> L >> R;
    const int MAXN = 1000;
    vector<vector<pair<int, int>>> graph(MAXN + 1);
    vector<vector<int>> children(MAXN + 1, vector<int>(2, 0));
    int next_node = 0;
    int end_node = ++next_node;
    vector<int> rem(21, 0);
    auto get_rem = [&](auto&& self, int j) -> int {
        if (rem[j] != 0) return rem[j];
        if (j == 0) return end_node;
        int lower = self(self, j - 1);
        int nd = ++next_node;
        rem[j] = nd;
        graph[nd].emplace_back(lower, 0);
        graph[nd].emplace_back(lower, 1);
        return nd;
    };
    int start_node = ++next_node;
    auto get_blocks = [](long long l, long long r) -> vector<pair<long long, int>> {
        vector<pair<long long, int>> res;
        while (l <= r) {
            long long sz = r - l + 1;
            int k = 0;
            long long pw = 1;
            while (pw * 2 <= sz && l % (pw * 2) == 0) {
                pw *= 2;
                k++;
            }
            res.emplace_back(l, k);
            l += pw;
        }
        return res;
    };
    int minl = (L == 0 ? 1 : 64 - __builtin_clzll(L));
    int maxl = 64 - __builtin_clzll(R);
    for (int length = minl; length <= maxl; length++) {
        long long offset = 1LL << (length - 1);
        long long lo = max(L, offset);
        long long hi = min(R, offset * 2 - 1);
        if (lo > hi) continue;
        int remaining = length - 1;
        long long ss = lo - offset;
        long long tt = hi - offset;
        if (remaining == 0) {
            graph[start_node].emplace_back(end_node, 1);
            continue;
        }
        int root_len = ++next_node;
        graph[start_node].emplace_back(root_len, 1);
        auto blocks = get_blocks(ss, tt);
        for (auto [u, kk] : blocks) {
            int m = remaining - kk;
            vector<int> fixed_bits(m);
            for (int i = 0; i < m; i++) {
                int shift = remaining - 1 - i;
                fixed_bits[i] = ((u >> shift) & 1);
            }
            int curr = root_len;
            if (kk == 0) {
                for (int i = 0; i < m - 1; i++) {
                    int bit = fixed_bits[i];
                    if (children[curr][bit] == 0) {
                        int newn = ++next_node;
                        children[curr][bit] = newn;
                        graph[curr].emplace_back(newn, bit);
                    }
                    curr = children[curr][bit];
                }
                if (m > 0) {
                    int bit = fixed_bits[m - 1];
                    graph[curr].emplace_back(end_node, bit);
                }
            } else {
                for (int i = 0; i < m; i++) {
                    int bit = fixed_bits[i];
                    if (children[curr][bit] == 0) {
                        int newn = ++next_node;
                        children[curr][bit] = newn;
                        graph[curr].emplace_back(newn, bit);
                    }
                    curr = children[curr][bit];
                }
                int targ = get_rem(get_rem, kk - 1);
                if (children[curr][0] == 0) {
                    graph[curr].emplace_back(targ, 0);
                    children[curr][0] = targ;
                }
                if (children[curr][1] == 0) {
                    graph[curr].emplace_back(targ, 1);
                    children[curr][1] = targ;
                }
            }
        }
    }
    int n = next_node;
    cout << n << endl;
    for (int i = 1; i <= n; i++) {
        int k = graph[i].size();
        cout << k;
        for (auto p : graph[i]) {
            cout << " " << p.first << " " << p.second;
        }
        cout << endl;
    }
    return 0;
}