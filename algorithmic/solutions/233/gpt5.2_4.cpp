#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    for (int tc = 0; tc < t; tc++) {
        int n, m;
        cin >> n >> m;

        vector<vector<int>> G(n + 1, vector<int>(n + 1));
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= n; j++) cin >> G[i][j];
        }

        int len = 2 * n - 1;

        vector<int> rowPref(n + 1, 0);
        for (int j = 1; j <= n; j++) rowPref[j] = max(rowPref[j - 1], G[1][j]);

        vector<int> a(len + 1, 0);
        a[1] = G[1][1];
        for (int T = 2; T <= len; T++) {
            cout << "? " << 1 << " " << T << "\n";
            cout.flush();
            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;
            a[T] = ans;
        }

        vector<int> prefMax(len + 1, 0);
        for (int i = 1; i <= len; i++) prefMax[i] = max(prefMax[i - 1], a[i]);

        vector<int> all;
        all.reserve((size_t)n * (size_t)len);

        vector<int> wmax(len + 1);

        for (int l = 1; l <= n; l++) {
            deque<int> dq;
            for (int i = 1; i <= len; i++) {
                while (!dq.empty() && a[dq.back()] <= a[i]) dq.pop_back();
                dq.push_back(i);
                while (!dq.empty() && dq.front() <= i - l) dq.pop_front();
                wmax[i] = a[dq.front()];
            }

            for (int T = 1; T <= len; T++) {
                int val;
                if (T <= l) {
                    int k = l - T + 1; // 1..l
                    val = max(prefMax[T], rowPref[k]);
                } else {
                    val = wmax[T];
                }
                all.push_back(val);
            }
        }

        nth_element(all.begin(), all.begin() + m, all.end());
        all.resize(m);
        sort(all.begin(), all.end());

        cout << "!";
        for (int i = 0; i < m; i++) cout << " " << all[i];
        cout << "\n";
        cout.flush();
    }

    return 0;
}