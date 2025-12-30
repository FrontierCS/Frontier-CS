#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<string> s(30);
    for (int i = 0; i < 30; i++) {
        if (!(cin >> s[i])) return 0;
    }

    string out(900, '0'); // rotate 0 times for all tiles
    cout << out << "\n";
    return 0;
}