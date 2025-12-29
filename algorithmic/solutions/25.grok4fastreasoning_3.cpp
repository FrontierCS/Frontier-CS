#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    for (int cas = 0; cas < T; ++cas) {
        int n;
        cin >> n;
        vector<char> mask(n + 1, 0);
        mask[1] = 1;
        int comp_size = 1;
        bool is_connected = false;
        while (true) {
            string qs(n, '0');
            for (int i = 1; i <= n; ++i) {
                if (mask[i]) qs[i - 1] = '1';
            }
            cout << "? " << qs << endl;
            cout.flush();
            int cb;
            cin >> cb;
            if (cb == 0) {
                is_connected = (comp_size == n);
                break;
            }
            vector<int> candidates;
            for (int i = 1; i <= n; ++i) {
                if (!mask[i]) candidates.push_back(i);
            }
            vector<int> detectables;
            while (!candidates.empty()) {
                int lo = 0;
                int hi = (int)candidates.size() - 1;
                while (lo < hi) {
                    int m = lo + (hi - lo) / 2;
                    string qt(n, '0');
                    for (int i = 1; i <= n; ++i) {
                        if (mask[i]) qt[i - 1] = '1';
                    }
                    for (int j = lo; j <= m; ++j) {
                        int ww = candidates[j];
                        qt[ww - 1] = '1';
                    }
                    cout << "? " << qt << endl;
                    cout.flush();
                    int bt;
                    cin >> bt;
                    if (bt != cb) {
                        hi = m;
                    } else {
                        lo = m + 1;
                    }
                }
                int pos = lo;
                int w = candidates[pos];
                string qt(n, '0');
                for (int i = 1; i <= n; ++i) {
                    if (mask[i]) qt[i - 1] = '1';
                }
                qt[w - 1] = '1';
                cout << "? " << qt << endl;
                cout.flush();
                int bt;
                cin >> bt;
                if (bt == cb) {
                    break;
                }
                detectables.push_back(w);
                candidates[pos] = candidates.back();
                candidates.pop_back();
            }
            for (int w : detectables) {
                mask[w] = 1;
                ++comp_size;
            }
        }
        cout << "! " << (is_connected ? 1 : 0) << endl;
        cout.flush();
    }
    return 0;
}