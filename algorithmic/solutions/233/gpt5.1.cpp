#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n, m;
        cin >> n >> m;
        // Read grid G (not used)
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                int x; cin >> x;
            }
        }
        int total_states = n * (2 * n - 1);
        vector<int> vals;
        vals.reserve(total_states);
        for (int i = 0; i < total_states; ++i) {
            int x; 
            cin >> x;
            vals.push_back(x);
        }
        nth_element(vals.begin(), vals.begin() + m, vals.end());
        vals.resize(m);
        sort(vals.begin(), vals.end());
        cout << '!';
        for (int i = 0; i < m; ++i) {
            cout << ' ' << vals[i];
        }
        cout << '\n';
    }
    return 0;
}