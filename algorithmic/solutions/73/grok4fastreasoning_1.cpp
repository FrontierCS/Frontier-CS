#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<vector<int>> parity(n + 1, vector<int>(n + 1, 0));
    vector<vector<int>> comp(n + 1, vector<int>(n + 1, 0));
    for (int i = 1; i <= n; ++i) {
        parity[i][i] = 0;
    }
    for (int k = 2; k <= n; ++k) {
        for (int l = 1; l < k; ++l) {
            cout << "0 " << l << " " << k << endl;
            cout.flush();
            int resp;
            cin >> resp;
            parity[l][k] = resp;
        }
        vector<int> ss(k + 1, 0);
        for (int l = 1; l < k; ++l) {
            int prev_r = parity[l][k - 1];
            ss[l] = parity[l][k] ^ prev_r;
        }
        for (int i = 1; i < k; ++i) {
            int s_next = (i + 1 < k) ? ss[i + 1] : 0;
            int yi = ss[i] ^ s_next;
            comp[i][k] = yi;
        }
    }
    vector<int> p(n + 1);
    for (int i = 1; i <= n; ++i) {
        int smaller = 0;
        for (int j = 1; j < i; ++j) {
            if (comp[j][i] == 0) ++smaller;
        }
        for (int j = i + 1; j <= n; ++j) {
            smaller += comp[i][j];
        }
        p[i] = smaller + 1;
    }
    cout << "1";
    for (int i = 1; i <= n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;
    cout.flush();
    return 0;
}