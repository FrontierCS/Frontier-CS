#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int m;
    if (!(cin >> m)) return 0;
    
    string s;
    while (cin >> s) {
        if (s == "treasure") {
            return 0;
        }
        cout << 1 << " left " << 0 << endl;
    }
    return 0;
}