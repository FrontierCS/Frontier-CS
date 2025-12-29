#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if(!(cin >> t)) return 0;
    const int m = 12;
    const int k = 6;

    while (t--) {
        int n;
        if(!(cin >> n)) return 0;
        int feedback;
        if(!(cin >> feedback)) return 0;
        if (feedback == -1) return 0;

        int L = 2 * n - 1;

        // Generate first L subsets of size k from [0..m-1]
        vector<vector<int>> codes;
        codes.reserve(L);
        vector<int> comb(k);
        for (int i = 0; i < k; ++i) comb[i] = i;
        while ((int)codes.size() < L) {
            codes.push_back(comb);
            int idx = k - 1;
            while (idx >= 0 && comb[idx] == idx + m - k) idx--;
            if (idx < 0) break;
            comb[idx]++;
            for (int j = idx + 1; j < k; ++j) comb[j] = comb[j - 1] + 1;
        }

        // Build S_j: positions where bit j is set
        vector<vector<int>> S(m);
        for (int pos = 1; pos <= L; ++pos) {
            for (int bit : codes[pos - 1]) {
                S[bit].push_back(pos);
            }
        }

        auto ask = [&](int x, const vector<int>& set)->int{
            cout << "? " << x << " " << set.size();
            for (int v : set) cout << " " << v;
            cout << '\n' << flush;
            int res;
            if(!(cin >> res)) return -1;
            return res;
        };

        int answer = 1; // default, should be overwritten
        for (int x = 1; x <= n; ++x) {
            int ones = 0;
            for (int j = 0; j < m; ++j) {
                int res = ask(x, S[j]);
                if (res == -1) return 0;
                ones += res;
            }
            if (ones == k) {
                answer = x;
                break;
            }
        }

        cout << "! " << answer << '\n' << flush;
    }

    return 0;
}