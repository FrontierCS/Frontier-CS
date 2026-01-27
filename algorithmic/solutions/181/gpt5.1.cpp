#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<long long> rowD(n, 0), colD(n, 0);
    vector<long long> rowF(n, 0), colF(n, 0);

    int x;
    // Read D
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cin >> x;
            if (x) {
                ++rowD[i];
                ++colD[j];
            }
        }
    }

    // Read F
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cin >> x;
            if (x) {
                ++rowF[i];
                ++colF[j];
            }
        }
    }

    vector<pair<long long,int>> fac(n), loc(n);
    for (int i = 0; i < n; ++i) {
        long long degF = rowF[i] + colF[i];
        long long degD = rowD[i] + colD[i];
        fac[i] = {-degF, i};   // sort descending by degree
        loc[i] = {degD, i};    // sort ascending by degree
    }

    sort(fac.begin(), fac.end());
    sort(loc.begin(), loc.end());

    vector<int> p(n);
    for (int k = 0; k < n; ++k) {
        int facility = fac[k].second;
        int location = loc[k].second;
        p[facility] = location + 1; // 1-based indexing for output
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << p[i];
    }
    cout << '\n';

    return 0;
}