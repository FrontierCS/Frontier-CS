#include <bits/stdc++.h>
using namespace std;

int main() {
    int n = 20, m = 20;
    cout << n << " " << m << endl;
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= m; j++) {
            if (i == 10 || j == 10) {
                cout << '1';
            } else {
                cout << '0';
            }
        }
        cout << endl;
    }
    return 0;
}