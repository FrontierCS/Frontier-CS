#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, q;
    if (!(cin >> n >> q)) return 0;
    vector<int> a(n+1);
    for (int i = 1; i <= n; ++i) cin >> a[i];
    vector<pair<int,int>> queries(q);
    for (int i = 0; i < q; ++i) cin >> queries[i].first >> queries[i].second;

    // Initial sets S_i = {a_i}, IDs 1..n
    int cnt = n;
    vector<pair<int,int>> ops;
    ops.reserve(2200000);

    // Map value v -> ID of its singleton set (position pos[v])
    vector<int> pos(n+1);
    for (int i = 1; i <= n; ++i) pos[a[i]] = i;

    // Bitset mapping: key = compressed bitset bytes -> set id
    int W = (n + 63) / 64;
    struct KeyHash {
        size_t operator()(const string& s) const noexcept {
            // FNV-1a 64-bit
            uint64_t h = 1469598103934665603ull;
            for (unsigned char c : s) { h ^= c; h *= 1099511628211ull; }
            return (size_t)h;
        }
    };
    unordered_map<string,int,KeyHash> mp;
    mp.reserve(q * 2 + 1024);

    auto bitset_to_key = [&](const vector<uint64_t>& bits)->string{
        string s;
        s.resize(W * 8);
        for (int i = 0; i < W; ++i) {
            uint64_t x = bits[i];
            for (int b = 0; b < 8; ++b) {
                s[i*8 + b] = char((x >> (8*b)) & 0xFF);
            }
        }
        return s;
    };

    vector<int> ans(q, 0);

    vector<uint64_t> bits(W, 0), pref(W, 0);

    for (int qi = 0; qi < q; ++qi) {
        int l = queries[qi].first, r = queries[qi].second;
        // Build list of values in [l, r], sorted ascending
        vector<int> vals;
        vals.reserve(r - l + 1);
        for (int i = l; i <= r; ++i) vals.push_back(a[i]);
        sort(vals.begin(), vals.end());

        // Build bitset key
        fill(bits.begin(), bits.end(), 0);
        for (int v : vals) {
            int idx = v - 1;
            bits[idx >> 6] |= (1ull << (idx & 63));
        }
        string key = bitset_to_key(bits);

        auto it = mp.find(key);
        if (it != mp.end()) {
            ans[qi] = it->second;
            continue;
        }

        // Try incremental prefix reuse
        fill(pref.begin(), pref.end(), 0);
        int current_id = -1;
        for (int i = 0; i < (int)vals.size(); ++i) {
            int v = vals[i];
            int idx = v - 1;
            pref[idx >> 6] |= (1ull << (idx & 63));
            string pkey = bitset_to_key(pref);
            auto pit = mp.find(pkey);
            if (pit != mp.end()) {
                current_id = pit->second;
                continue;
            }
            // Need to create by merging
            if (i == 0) {
                current_id = pos[v];
                mp.emplace(pkey, current_id);
            } else {
                int singleton_id = pos[v];
                // Ensure g(A) < f(B): since vals are sorted ascending by value, holds
                ops.emplace_back(current_id, singleton_id);
                ++cnt;
                current_id = cnt;
                mp.emplace(pkey, current_id);
            }
        }
        ans[qi] = current_id;
    }

    cout << cnt << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    for (int i = 0; i < q; ++i) {
        if (i) cout << " ";
        cout << ans[i];
    }
    cout << "\n";
    return 0;
}