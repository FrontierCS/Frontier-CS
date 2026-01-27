#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t = 0;
    if (!(cin >> t)) t = 0;
    char c = (t == 0) ? '0' : '1';
    string line(12, c);
    for (int i = 0; i < 12; ++i) {
        cout << line << '\n';
    }
    return 0;
}