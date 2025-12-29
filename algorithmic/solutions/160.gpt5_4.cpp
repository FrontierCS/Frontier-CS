#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> f(100);
    for (int i = 0; i < 100; i++) {
        if (!(cin >> f[i])) return 0;
    }

    for (int t = 1; t <= 100; t++) {
        int p;
        if (!(cin >> p)) return 0;
        char out;
        if (t % 2 == 0) out = 'F';
        else out = (((t - 1) / 2) % 2 == 0) ? 'L' : 'R';
        cout << out << '\n' << flush;
    }

    return 0;
}