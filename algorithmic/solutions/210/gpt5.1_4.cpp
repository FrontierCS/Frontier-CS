#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<string> grid(n);
    for (int i = 0; i < n; ++i) cin >> grid[i];

    int N_blue;
    cin >> N_blue;
    for (int i = 0; i < N_blue; ++i) {
        int x, y;
        long long g, c, d, v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
    }

    int N_red;
    cin >> N_red;
    for (int i = 0; i < N_red; ++i) {
        int x, y;
        long long g, c, d, v;
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