#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long s;
    cout << "walk 0\n" << flush;
    if (!(cin >> s)) return 0;

    long long steps = 0, v = -1;
    while (true) {
        cout << "walk 1\n" << flush;
        if (!(cin >> v)) return 0;
        steps++;
        if (v == s) break;
        if (steps > 200000) break;
    }

    cout << "guess " << steps << "\n" << flush;
    return 0;
}