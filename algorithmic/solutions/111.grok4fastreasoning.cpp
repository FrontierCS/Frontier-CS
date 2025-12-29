#include <bits/stdc++.h>
using namespace std;

int main() {
    long long n;
    cin >> n;
    int mmin = (int)sqrt((double)n / 2);
    vector<int> S;
    int maxx = 2 * n + 100;
    vector<char> usd(maxx, 0);
    int cur = 1;
    while (S.size() < mmin && cur <= n) {
        bool can = true;
        for (int j = S.size() - 1; j >= 0 && can; j--) {
            int s = S[j];
            int xv = cur ^ s;
            if (xv < maxx && usd[xv]) {
                can = false;
            }
        }
        if (can) {
            // add
            vector<int> olds = S; // copy previous
            S.push_back(cur);
            for (int s : olds) {
                int xv = cur ^ s;
                if (xv < maxx) usd[xv] = 1;
            }
        }
        cur++;
    }
    if (S.empty() && n >= 1) {
        S = {1};
    }
    cout << S.size() << endl;
    for (int x : S) {
        cout << x << " ";
    }
    cout << endl;
    return 0;
}