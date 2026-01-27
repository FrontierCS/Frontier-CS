#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    if(!(cin >> t)) return 0;
    vector<string> small(12, string(12, '0'));
    vector<string> large(12, string(12, '1'));
    const auto &out = (t==1) ? large : small;
    for (int i = 0; i < 12; ++i) {
        cout << out[i] << "\n";
    }
    return 0;
}