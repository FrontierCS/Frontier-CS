#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        vector<int> p(n);
        for (int i = 0; i < n; i++) cin >> p[i];

        int mx1 = -1, mx2 = -1;
        int i1 = -1, i2 = -1;
        for (int i = 0; i < n; i++) {
            if (p[i] > mx1) {
                mx2 = mx1; i2 = i1;
                mx1 = p[i]; i1 = i;
            } else if (p[i] > mx2) {
                mx2 = p[i]; i2 = i;
            }
        }

        if (i1 == -1 || i2 == -1) {
            cout << "0 1\n";
        } else {
            cout << i1 << " " << i2 << "\n";
        }
    }
    return 0;
}