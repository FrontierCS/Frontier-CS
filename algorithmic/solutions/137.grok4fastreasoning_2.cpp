#include <bits/stdc++.h>
using namespace std;

int main() {
    cout << 20 << " " << 20 << endl;
    for (int i = 1; i <= 20; ++i) {
        for (int j = 1; j <= 20; ++j) {
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