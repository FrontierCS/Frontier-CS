#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    double sq = sqrt(n / 2.0);
    int needed = (int)floor(sq);
    if (needed == 0) needed = 1;
    vector<int> S;
    const int MAX_XOR = 1 << 24;
    vector<char> forbidden(MAX_XOR, 0);
    int cur = 0;
    while ((int)S.size() < needed && cur < n) {
        cur++;
        bool can_add = true;
        vector<int> new_xors;
        for (int s : S) {
            int xr = cur ^ s;
            if (xr >= MAX_XOR || forbidden[xr]) {
                can_add = false;
                break;
            }
            new_xors.push_back(xr);
        }
        if (can_add) {
            for (int xr : new_xors) {
                forbidden[xr] = 1;
            }
            S.push_back(cur);
        }
    }
    cout << S.size() << endl;
    for (size_t i = 0; i < S.size(); ++i) {
        cout << S[i];
        if (i + 1 < S.size()) cout << " ";
        else cout << endl;
    }
    return 0;
}