#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int Q = 12;
    const int n_max = 300;
    const int m_max = 2 * n_max - 1; // 599

    // Precompute codes of length Q with weight Q/2 = 6
    vector<array<int, Q>> codes(m_max + 1);
    int idx = 1;
    for (int mask = 0; mask < (1 << Q) && idx <= m_max; ++mask) {
        if (__builtin_popcount(mask) == Q / 2) {
            array<int, Q> c{};
            for (int b = 0; b < Q; ++b) {
                c[b] = (mask >> b) & 1;
            }
            codes[idx++] = c;
        }
    }

    // Precompute S[b] for indices up to m_max
    vector<vector<int>> S_base(Q);
    for (int i = 1; i <= m_max; ++i) {
        for (int b = 0; b < Q; ++b) {
            if (codes[i][b]) S_base[b].push_back(i);
        }
    }

    int T;
    if (!(cin >> T)) return 0;
    for (int tc = 0; tc < T; ++tc) {
        int n;
        if (!(cin >> n)) return 0;
        if (n == -1) return 0; // judge indicates wrong answer

        int m = 2 * n - 1;

        // Build S for this test case (indices 1..m)
        vector<vector<int>> S(Q);
        for (int b = 0; b < Q; ++b) {
            for (int id : S_base[b]) {
                if (id <= m) S[b].push_back(id);
                else break; // S_base[b] is sorted ascending
            }
        }

        int answer = -1;

        for (int x = 1; x <= n; ++x) {
            int ones = 0;
            for (int b = 0; b < Q; ++b) {
                auto &Sv = S[b];
                cout << "? " << x << " " << Sv.size();
                for (int id : Sv) cout << " " << id;
                cout << endl;
                cout.flush();

                int resp;
                if (!(cin >> resp)) return 0;
                if (resp == -1) return 0;
                if (resp == 1) ++ones;
            }
            if (ones == Q / 2) {
                answer = x;
                break;
            }
        }

        if (answer == -1) answer = 1; // fallback, should not happen

        cout << "! " << answer << endl;
        cout.flush();
    }

    return 0;
}