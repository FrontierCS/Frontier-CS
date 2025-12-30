#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;
        if (n <= 1) {
            cout << "! 1" << endl;
            cout.flush();
            continue;
        }
        bool disconnected = false;
        for (int i = 0; i < n && !disconnected; ++i) {
            string s(n, '0');
            s[i] = '1';
            cout << "? " << s << endl;
            cout.flush();
            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == 0) {
                disconnected = true;
            }
        }
        if (disconnected) {
            cout << "! 0" << endl;
        } else {
            cout << "! 1" << endl;
        }
        cout.flush();
    }
    return 0;
}