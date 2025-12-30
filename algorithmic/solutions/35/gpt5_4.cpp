#include <bits/stdc++.h>
using namespace std;

static long long comb_cache[64][64];

long long Ccalc(int n, int k) {
    if (k < 0 || k > n) return 0;
    if (comb_cache[n][k] != -1) return comb_cache[n][k];
    if (k == 0 || k == n) return comb_cache[n][k] = 1;
    return comb_cache[n][k] = Ccalc(n - 1, k - 1) + Ccalc(n - 1, k);
}

int ask(int x, const vector<int>& S) {
    cout << "? " << x << " " << (int)S.size();
    for (int idx : S) cout << " " << idx;
    cout << "\n";
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    memset(comb_cache, -1, sizeof(comb_cache));

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) return 0;
        int m = 2 * n - 1;

        int K = 1;
        while (true) {
            int r = K / 2;
            long long val = Ccalc(K, r);
            if (val >= m) break;
            ++K;
        }
        int r = K / 2;

        vector<unsigned int> codes(m);
        // Generate first m combinations of size r over K bits
        vector<int> comb(r);
        for (int i = 0; i < r; ++i) comb[i] = i;
        int generated = 0;
        while (generated < m) {
            unsigned int mask = 0;
            for (int x : comb) mask |= (1u << x);
            codes[generated++] = mask;

            int i = r - 1;
            while (i >= 0 && comb[i] == K - r + i) --i;
            if (i < 0) break;
            ++comb[i];
            for (int j = i + 1; j < r; ++j) comb[j] = comb[j - 1] + 1;
        }

        // Build sets S_j
        vector<vector<int>> sets(K);
        for (int idx = 0; idx < m; ++idx) {
            unsigned int mask = codes[idx];
            for (int j = 0; j < K; ++j) {
                if (mask & (1u << j)) sets[j].push_back(idx + 1);
            }
        }

        int answer = 1;
        for (int x = 1; x <= n; ++x) {
            int cnt = 0;
            for (int j = 0; j < K; ++j) {
                int res = ask(x, sets[j]);
                cnt += res;
            }
            if (cnt == r) {
                answer = x;
                break;
            }
        }

        cout << "! " << answer << "\n";
        cout.flush();

        int verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == -1) return 0;
        // else continue to next test case
    }

    return 0;
}