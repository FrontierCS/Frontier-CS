#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    string row;
    for (int i = 0; i < n; i++) cin >> row;

    int Nb, Nr;
    cin >> Nb;
    int x, y;
    long long g, c, d, v;
    for (int i = 0; i < Nb; i++) {
        cin >> x >> y;
        cin >> g >> c >> d >> v;
    }

    cin >> Nr;
    for (int i = 0; i < Nr; i++) {
        cin >> x >> y;
        cin >> g >> c >> d >> v;
    }

    int k;
    cin >> k;
    long long G, Cc;
    for (int i = 0; i < k; i++) {
        cin >> x >> y >> G >> Cc;
    }

    const int MAX_FRAMES = 15000;
    for (int f = 0; f < MAX_FRAMES; ++f) {
        cout << "OK\n";
    }

    return 0;
}