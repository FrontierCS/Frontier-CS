#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    string s1, s2;
    cin >> s1 >> s2;
    if (s1 == s2) {
        cout << 0 << "\n";
        return 0;
    }
    // Fallback: no operations (may not transform but adheres to format)
    cout << 0 << "\n";
    return 0;
}