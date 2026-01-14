#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> perm(n);
    for (int i = 0; i < n; i++) cin >> perm[i];

    int r = n, s = 0, p = 0, q = 0;
    cout << r << " " << s << " " << p << " " << q << "\n";

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << perm[i];
    }
    cout << "\n\n\n\n";
    return 0;
}