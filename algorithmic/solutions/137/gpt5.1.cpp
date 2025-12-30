#include <bits/stdc++.h>
using namespace std;

int main() {
    int n = 20, m = 20;
    cout << n << " " << m << "\n";
    for (int i = 0; i < n; ++i) {
        if (i == 0) {
            for (int j = 0; j < m; ++j) cout << '1';
        } else {
            for (int j = 0; j < m; ++j) {
                if (j % 2 == 0) cout << '1';
                else cout << '0';
            }
        }
        cout << "\n";
    }
    return 0;
}