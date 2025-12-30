#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t = 0;
    if (!(cin >> t)) t = 0;
    string s = (t == 0) ? "000000000000" : "111111111111";
    for (int i = 0; i < 12; ++i) {
        cout << s << '\n';
    }
    return 0;
}