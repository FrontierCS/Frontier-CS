#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    vector<long long> a;
    a.reserve(64);
    a.push_back(1);

    while ((long long)a.size() < 1000000) {
        __int128 nxt = (__int128)a.back() * 2;
        if (nxt > n) break;
        a.push_back((long long)nxt);
    }

    cout << a.size() << "\n";
    for (size_t i = 0; i < a.size(); i++) {
        if (i) cout << ' ';
        cout << a[i];
    }
    cout << "\n";
    return 0;
}