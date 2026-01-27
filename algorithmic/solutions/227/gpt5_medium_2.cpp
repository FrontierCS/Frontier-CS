#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) cin >> p[i];

    // Put all elements into 'a', others empty
    cout << n << " " << 0 << " " << 0 << " " << 0 << "\n";
    for (int i = 0; i < n; ++i) {
        if (i) cout << " ";
        cout << p[i];
    }
    cout << "\n";
    cout << "\n";
    cout << "\n";
    cout << "\n";
    return 0;
}