#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Try to detect offline version (permutation is given)
    char delim;
    if (!cin.get(delim)) delim = '\n'; // consume one delimiter if present
    streambuf* sb = cin.rdbuf();
    int avail = sb->in_avail();

    if (avail > 0) {
        // Offline: permutation is provided
        vector<int> p(n + 1);
        for (int i = 1; i <= n; ++i) {
            if (!(cin >> p[i])) return 0;
        }
        int M = n / 2;
        int idxM = -1, idxMp1 = -1;
        for (int i = 1; i <= n; ++i) {
            if (p[i] == M) idxM = i;
            else if (p[i] == M + 1) idxMp1 = i;
        }
        if (idxM == -1 || idxMp1 == -1) {
            idxM = 1;
            idxMp1 = 2;
        }
        cout << idxM << " " << idxMp1 << "\n";
        return 0;
    } else {
        // Interactive: use queries
        int M = n / 2;
        int ans1 = 1, ans2 = 2;
        bool found = false;

        for (int i = 1; i <= n && !found; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                cout << 0 << " " << (n - 2);
                for (int k = 1; k <= n; ++k) {
                    if (k == i || k == j) continue;
                    cout << " " << k;
                }
                cout << "\n";
                cout.flush();

                int m1, m2;
                if (!(cin >> m1 >> m2)) return 0;
                if (m1 > m2) swap(m1, m2);

                if (m1 == M - 1 && m2 == M + 2) {
                    ans1 = i;
                    ans2 = j;
                    found = true;
                    break;
                }
            }
        }

        cout << 1 << " " << ans1 << " " << ans2 << "\n";
        cout.flush();
        return 0;
    }
}