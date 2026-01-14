#include <bits/stdc++.h>
using namespace std;

int main() {
    long long L, R;
    cin >> L >> R;
    auto bitlen_func = [](long long x) -> int {
        if (x == 0) return 0;
        return 64 - __builtin_clzll(x);
    };
    int D2 = bitlen_func(R);
    int max_rem = D2 - 1;
    int num_f = max_rem + 1;
    vector<vector<pair<int, int>>> adj(101);
    vector<int> FF(max_rem + 1);
    FF[0] = 1; // end_node
    for (int k = 1; k <= max_rem; ++k) {
        FF[k] = k + 1;
        adj[FF[k]].emplace_back(FF[k - 1], 0);
        adj[FF[k]].emplace_back(FF[k - 1], 1);
    }
    int next_node_id = num_f + 1;
    int start_node = next_node_id++;
    auto add_range = [&](auto&& self, int curr_start, long long lo, long long hi, int m) -> void {
        if (lo > hi) return;
        long long full_lo = 0;
        long long full_hi = (m == 0 ? 0LL : ((1LL << m) - 1));
        if (lo == full_lo && hi == full_hi) {
            int rem = m - 1;
            int tgt = (rem <= 0 ? 1 : FF[rem]);
            bool has0 = false;
            bool has1 = false;
            for (const auto& pr : adj[curr_start]) {
                if (pr.second == 0 && pr.first == tgt) has0 = true;
                if (pr.second == 1 && pr.first == tgt) has1 = true;
            }
            if (!has0) adj[curr_start].emplace_back(tgt, 0);
            if (!has1) adj[curr_start].emplace_back(tgt, 1);
            return;
        }
        // decompose
        vector<pair<long long, int>> blocks;
        long long cuv = lo;
        while (cuv <= hi) {
            long long lenr = hi - cuv + 1;
            int kmax = (lenr == 0 ? 0 : 63 - __builtin_clzll(lenr));
            int k;
            if (cuv == 0) {
                k = kmax;
            } else {
                int tz = 0;
                long long t = cuv;
                while (t % 2 == 0 && t != 0) {
                    t /= 2;
                    ++tz;
                }
                k = min(tz, kmax);
            }
            blocks.emplace_back(cuv, k);
            cuv += (1LL << k);
        }
        for (auto [A, k] : blocks) {
            int s = k;
            int p = m - s;
            long long num = A >> s;
            vector<int> prefix_bits(p);
            for (int i = 0; i < p; ++i) {
                int pos = p - 1 - i;
                prefix_bits[i] = (num >> pos) & 1;
            }
            int current = curr_start;
            bool force_last = (s == 0);
            for (int j = 0; j < p; ++j) {
                int label = prefix_bits[j];
                int target = -1;
                bool force_end = force_last && (j == p - 1);
                // find existing
                for (const auto& pr : adj[current]) {
                    if (pr.second == label) {
                        target = pr.first;
                        break;
                    }
                }
                if (target == -1) {
                    if (force_end) {
                        target = 1;
                    } else {
                        target = next_node_id++;
                    }
                    adj[current].emplace_back(target, label);
                } else if (force_end && target != 1) {
                    // conflict, skip this block (should not happen)
                    break;
                }
                current = target;
            }
            if (s > 0) {
                int rem = s - 1;
                int tgt = (rem <= 0 ? 1 : FF[rem]);
                bool has0 = false;
                bool has1 = false;
                for (const auto& pr : adj[current]) {
                    if (pr.second == 0 && pr.first == tgt) has0 = true;
                    if (pr.second == 1 && pr.first == tgt) has1 = true;
                }
                if (!has0) adj[current].emplace_back(tgt, 0);
                if (!has1) adj[current].emplace_back(tgt, 1);
            }
        }
    };
    for (int d = 1; d <= D2; ++d) {
        long long offset = 1LL << (d - 1);
        long long low_d = max(L, offset);
        long long high_d = min(R, offset * 2 - 1);
        if (low_d > high_d) continue;
        long long suf_lo = low_d - offset;
        long long suf_hi = high_d - offset;
        int m = d - 1;
        long long full_lo = 0;
        long long full_hi = (m == 0 ? 0LL : ((1LL << m) - 1));
        if (suf_lo == full_lo && suf_hi == full_hi) {
            int tgt = (m <= 0 ? 1 : FF[m]);
            adj[start_node].emplace_back(tgt, 1);
        } else {
            int after1 = next_node_id++;
            adj[start_node].emplace_back(after1, 1);
            add_range(add_range, after1, suf_lo, suf_hi, m);
        }
    }
    int n = next_node_id - 1;
    cout << n << endl;
    for (int i = 1; i <= n; ++i) {
        auto& edges = adj[i];
        cout << edges.size();
        for (auto& p : edges) {
            cout << " " << p.first << " " << p.second;
        }
        cout << endl;
    }
    return 0;
}