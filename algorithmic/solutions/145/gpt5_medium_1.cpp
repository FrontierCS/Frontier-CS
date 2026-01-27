#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    string row;
    if (t == 0) row = string(12, '0');
    else row = string(12, '1');
    for (int i = 0; i < 12; ++i) {
        cout << row << "\n";
    }
    return 0;
}