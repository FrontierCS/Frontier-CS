#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    string row;
    for (int i = 0; i < n; ++i) cin >> row;
    
    int Nb;
    cin >> Nb;
    for (int i = 0; i < Nb; ++i) {
        int x, y; long long g, c, d, v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
    }
    int Nr;
    cin >> Nr;
    for (int i = 0; i < Nr; ++i) {
        int x, y; long long g, c, d, v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
    }
    int k;
    cin >> k;
    for (int i = 0; i < k; ++i) {
        int x, y, G, C;
        cin >> x >> y >> G >> C;
    }
    
    cout << "OK\n";
    return 0;
}