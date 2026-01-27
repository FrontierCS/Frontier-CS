#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    const int M = 12;
    const int R = 6;

    while (t--) {
        int n;
        if (!(cin >> n)) return 0;

        int status;
        if (!(cin >> status)) return 0;
        if (status == -1) return 0;

        int L = 2 * n - 1;

        vector<int> mask_for_index(L + 1, 0);
        int assigned = 0;
        for (int mask = 0; mask < (1 << M) && assigned < L; ++mask) {
            if (__builtin_popcount((unsigned)mask) == R) {
                mask_for_index[++assigned] = mask;
            }
        }

        vector<vector<int>> sets(M);
        for (int i = 1; i <= L; ++i) {
            int msk = mask_for_index[i];
            for (int b = 0; b < M; ++b) {
                if (msk & (1 << b)) sets[b].push_back(i);
            }
        }

        int answer_x = -1;
        for (int x = 1; x <= n; ++x) {
            int cnt = 0;
            for (int b = 0; b < M; ++b) {
                cout << "? " << x << " " << sets[b].size();
                for (int idx : sets[b]) cout << " " << idx;
                cout << '\n' << flush;

                int resp;
                if (!(cin >> resp)) return 0;
                if (resp == -1) return 0;
                if (resp == 1) cnt++;
            }
            if (cnt == R) {
                answer_x = x;
                break;
            }
        }

        if (answer_x == -1) answer_x = 1;

        cout << "! " << answer_x << '\n' << flush;
    }

    return 0;
}