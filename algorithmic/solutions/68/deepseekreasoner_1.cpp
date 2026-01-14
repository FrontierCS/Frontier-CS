#include <bits/stdc++.h>
using namespace std;

int main() {
    int t;
    cin >> t;
    while (t--) {
        int n;
        cin >> n;
        vector<int> has_ink(n, true);
        vector<int> count(n, 0);
        for (int i = 0; i < n; i++) {
            cout << 0 << " " << i << endl;
            int response;
            cin >> response;
            if (response == 1) {
                count[i] = 1;
            } else {
                has_ink[i] = false;
            }
        }
        int a = -1, b = -1;
        for (int i = 0; i < n; i++) {
            if (has_ink[i]) {
                if (a == -1) a = i;
                else if (b == -1) b = i;
            }
        }
        if (a == -1 || b == -1) {
            a = 0;
            b = 1;
        }
        cout << 1 << " " << a << " " << b << endl;
    }
    return 0;
}