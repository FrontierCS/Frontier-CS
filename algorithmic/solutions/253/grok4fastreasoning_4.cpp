#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    cin >> t;
    for (int test = 0; test < t; ++test) {
        int n, m;
        cin >> n >> m;
        vector<int> A(m + 1), B(m + 1);
        for (int i = 1; i <= m; ++i) {
            cin >> A[i] >> B[i];
        }
        // Find s
        for (int x = 1; x <= m; ++x) {
            cout << "- " << x << '\n';
            cout.flush();
        }
        int s = -1;
        for (int y = 1; y <= n; ++y) {
            cout << "? 1 " << y << '\n';
            cout.flush();
            int res;
            cin >> res;
            if (res == 1) {
                s = y;
                break;
            }
            if (res == -1) {
                return 0;
            }
        }
        // Unblock all
        for (int x = 1; x <= m; ++x) {
            cout << "+ " << x << '\n';
            cout.flush();
        }
        // Now test for each y != s
        vector<int> repaired(m + 1, 0);
        for (int y = 1; y <= n; ++y) {
            if (y == s) continue;
            // Find incident roads
            vector<int> inc;
            for (int i = 1; i <= m; ++i) {
                if (A[i] == y || B[i] == y) {
                    inc.push_back(i);
                }
            }
            int dd = inc.size();
            if (dd == 0) continue;
            // Block all incident
            for (int idx : inc) {
                cout << "- " << idx << '\n';
                cout.flush();
            }
            // Test each
            for (int k = 0; k < dd; ++k) {
                int idx = inc[k];
                // Unblock
                cout << "+ " << idx << '\n';
                cout.flush();
                // Query
                cout << "? 1 " << y << '\n';
                cout.flush();
                int res;
                cin >> res;
                if (res == 1) {
                    repaired[idx] = 1;
                }
                if (res == -1) {
                    return 0;
                }
                // Block back
                cout << "- " << idx << '\n';
                cout.flush();
            }
            // Unblock all
            for (int idx : inc) {
                cout << "+ " << idx << '\n';
                cout.flush();
            }
        }
        // Output
        cout << "!";
        for (int i = 1; i <= m; ++i) {
            cout << " " << repaired[i];
        }
        cout << '\n';
        cout.flush();
        int verdict;
        cin >> verdict;
        if (verdict == 0) {
            return 0;
        }
    }
    return 0;
}