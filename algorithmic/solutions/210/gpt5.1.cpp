#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> grid(n);
    for (int i = 0; i < n; ++i) cin >> grid[i];

    int Nblue;
    cin >> Nblue;
    for (int i = 0; i < Nblue; ++i) {
        int x, y;
        cin >> x >> y;
        long long g, c, d, v;
        cin >> g >> c >> d >> v;
    }

    int Nred;
    cin >> Nred;
    for (int i = 0; i < Nred; ++i) {
        int x, y;
        cin >> x >> y;
        long long g, c, d, v;
        cin >> g >> c >> d >> v;
    }

    int k;
    cin >> k;
    for (int i = 0; i < k; ++i) {
        int x, y, G, C;
        cin >> x >> y >> G >> C;
    }

    // Output a single empty frame.
    cout << "OK\n";
    return 0;
}