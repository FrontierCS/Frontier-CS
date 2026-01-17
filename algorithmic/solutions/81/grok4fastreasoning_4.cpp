#include <bits/stdc++.h>
using namespace std;

int main() {
    int N;
    cin >> N;
    string S(N, '0');
    for (int k = 0; k < N; k++) {
        int m = min(1002, k + 3);
        vector<int> a(m), b(m);
        for (int i = 0; i < m; i++) {
            a[i] = i;
            b[i] = i;
        }
        for (int i = 0; i < k; i++) {
            int curr = i;
            char bit = S[i];
            if (bit == '0') {
                a[curr] = i + 1;
            } else {
                b[curr] = i + 1;
            }
        }
        int probe = k;
        a[probe] = k + 1;
        b[probe] = k + 2;
        // absorbing already set to self
        cout << 1 << endl;
        cout << m << endl;
        for (int i = 0; i < m; i++) {
            if (i > 0) cout << " ";
            cout << a[i];
        }
        cout << endl;
        for (int i = 0; i < m; i++) {
            if (i > 0) cout << " ";
            cout << b[i];
        }
        cout << endl;
        cout.flush();
        int x;
        cin >> x;
        if (x == k + 1) {
            S[k] = '0';
        } else {
            S[k] = '1';
        }
    }
    cout << 0 << endl;
    cout << S << endl;
    cout.flush();
    return 0;
}