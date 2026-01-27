#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
using i128 = __int128_t;
using u128 = __uint128_t;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int q;
    if (!(cin >> q)) return 0;
    vector<unsigned long long> ks(q);
    for (int i = 0; i < q; ++i) cin >> ks[i];

    for (int qi = 0; qi < q; ++qi) {
        unsigned long long k = ks[qi];

        deque<pair<char,int>> blocks; // 'D' for decreasing (len=1), 'I' for increasing (len=t)

        function<void(unsigned long long)> build = [&](unsigned long long x) {
            if (x == 1) return;
            if (x & 1ULL) {
                blocks.emplace_front('D', 1);
                build(x - 1);
            } else {
                int t = __builtin_ctzll(x);
                build(x >> t);
                blocks.emplace_back('I', t);
            }
        };

        build(k);

        int n = 0;
        for (auto &b : blocks) n += b.second;

        cout << n << "\n";
        if (n == 0) {
            cout << "\n";
            continue;
        }

        vector<int> perm(n);
        int low = 0, high = n - 1, pos = 0;

        for (auto &b : blocks) {
            if (b.first == 'D') {
                // len is 1
                perm[pos++] = low++;
            } else {
                int t = b.second;
                for (int v = high - t + 1; v <= high; ++v) {
                    perm[pos++] = v;
                }
                high -= t;
            }
        }

        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << perm[i];
        }
        cout << "\n";
    }
    return 0;
}