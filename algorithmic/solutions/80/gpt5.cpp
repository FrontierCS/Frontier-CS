#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int m;
    if (!(cin >> m)) return 0;
    string s;
    while (cin >> s) {
        if (s == "treasure") break;
        if (s == "center") {
            cout << 0 << " left " << 0 << endl;
        } else if (s == "left" || s == "right") {
            cout << 1 % m << " left " << 1 % m << endl;
        } else {
            // Fallback in case of unexpected input
            cout << 0 << " left " << 0 << endl;
        }
        cout.flush();
    }
    return 0;
}