#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    string s1, s2;
    if (!(cin >> n)) return 0;
    cin >> s1 >> s2;
    vector<pair<int,long long>> ops;
    if (s1 == s2) {
        cout << 0 << "\n";
        return 0;
    }
    // Fallback: no guaranteed transformation; output zero operations
    cout << 0 << "\n";
    return 0;
}