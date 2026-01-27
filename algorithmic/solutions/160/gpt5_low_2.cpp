#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<int> f(101);
    for (int i = 1; i <= 100; i++) {
        if (!(cin >> f[i])) return 0;
    }
    int cnt3 = 0;
    for (int t = 1; t <= 100; t++) {
        int p;
        if (!(cin >> p)) return 0;
        if (t == 100) {
            // Final tilt does nothing; skip output as allowed
            break;
        }
        char out;
        if (f[t] == 1) out = 'L';
        else if (f[t] == 2) out = 'R';
        else {
            out = (cnt3 % 2 == 0) ? 'F' : 'B';
            cnt3++;
        }
        cout << out << '\n' << flush;
    }
    return 0;
}