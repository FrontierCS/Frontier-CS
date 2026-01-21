#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int h;
    if(!(cin >> h)) return 0;

    long long n = (1LL << h) - 1;

    if (h == 2) {
        vector<long long> r(3);
        for (int i = 1; i <= 3; ++i) {
            cout << "? " << i << " 1" << endl;
            cout.flush();
            if(!(cin >> r[i-1])) return 0;
        }
        long long root = 0, leaves = 0;
        if (r[0] == r[1]) { root = r[0]; leaves = r[2]; }
        else if (r[0] == r[2]) { root = r[0]; leaves = r[1]; }
        else { root = r[1]; leaves = r[0]; }
        long long S = root + leaves;
        cout << "! " << S << endl;
        cout.flush();
        return 0;
    } else {
        cout << "! 0" << endl;
        cout.flush();
    }

    return 0;
}