#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        long long m;
        cin >> n >> m;
        vector<int> vals;
        vals.reserve(n * n);
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                int x;
                cin >> x;
                vals.push_back(x);
            }
        }
        sort(vals.begin(), vals.end());
        cout << '!';
        int sz = (int)vals.size();
        for (long long i = 0; i < m; ++i) {
            int v = (i < sz) ? vals[(size_t)i] : vals.back();
            cout << ' ' << v;
        }
        cout << '\n';
        cout.flush();
    }
    return 0;
}