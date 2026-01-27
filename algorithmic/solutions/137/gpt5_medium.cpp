#include <bits/stdc++.h>
using namespace std;

int main() {
    int n = 20, m = 20;
    cout << n << " " << m << "\n";
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            cout << (j == 0 ? '1' : '0');
        }
        cout << "\n";
    }
    return 0;
}