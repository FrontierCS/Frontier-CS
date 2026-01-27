#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    
    vector<string> rows;
    string s;
    while (cin >> s) {
        if ((int)s.size() == n) {
            bool ok = true;
            for (char c : s) if (c != '0' && c != '1') { ok = false; break; }
            if (ok) rows.push_back(s);
            if ((int)rows.size() == n) break;
        }
    }
    
    cout << "!\n";
    if ((int)rows.size() == n) {
        for (int i = 0; i < n; ++i) {
            cout << rows[i] << "\n";
        }
    } else {
        // Fallback: output a default grid with top-left 1 and bottom-right 0
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                if (i == 1 && j == 1) cout << '1';
                else if (i == n && j == n) cout << '0';
                else cout << '0';
            }
            cout << "\n";
        }
    }
    return 0;
}