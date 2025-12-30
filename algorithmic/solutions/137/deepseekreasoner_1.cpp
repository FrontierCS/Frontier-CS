#include <iostream>
using namespace std;

int main() {
    int n = 20, m = 20;
    cout << n << " " << m << endl;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            if (i == 9 || j == 9) {
                cout << '1';
            } else {
                cout << '0';
            }
        }
        cout << endl;
    }
    return 0;
}