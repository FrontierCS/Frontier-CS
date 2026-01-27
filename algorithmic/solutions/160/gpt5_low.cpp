#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> f(100);
    for (int i = 0; i < 100; i++) {
        if (!(cin >> f[i])) return 0;
    }
    for (int t = 0; t < 100; t++) {
        int p;
        if (!(cin >> p)) return 0;
        char out;
        if (f[t] == 1) out = 'F';
        else if (f[t] == 2) out = 'B';
        else out = 'L';
        cout << out << '\n' << flush;
    }
    return 0;
}