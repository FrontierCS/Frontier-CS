#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) cin >> p[i];

    // Put all elements into subsequence a; others empty
    int r = n, s = 0, t = 0, q = 0;
    cout << r << " " << s << " " << t << " " << q << "\n";
    for (int i = 0; i < n; ++i) {
        if (i) cout << " ";
        cout << p[i];
    }
    cout << "\n";
    cout << "\n"; // b empty
    cout << "\n"; // c empty
    cout << "\n"; // d empty
    return 0;
}