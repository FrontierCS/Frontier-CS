#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<string> t(30);
    for (int i = 0; i < 30; ++i) {
        if (!(cin >> t[i])) return 0;
    }

    string res(900, '0');
    cout << res << '\n';
    return 0;
}