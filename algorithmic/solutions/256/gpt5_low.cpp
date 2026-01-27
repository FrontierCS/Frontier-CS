#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    cout << "!\n";
    for (int i = 1; i <= n; ++i) {
        string row;
        row.resize(n, '0');
        for (int j = 1; j <= n; ++j) {
            if (i == 1 && j == 1) row[j-1] = '1';
            else if (i == n && j == n) row[j-1] = '0';
            else row[j-1] = '0';
        }
        cout << row << "\n";
    }
    cout.flush();
    return 0;
}