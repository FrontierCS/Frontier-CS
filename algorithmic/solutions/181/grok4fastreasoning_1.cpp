#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    cin >> n;
    vector<bitset<2005>> Drow(n), Dcol(n);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int x;
            cin >> x;
            if (x) {
                Drow[i][j] = 1;
                Dcol[j][i] = 1;
            }
        }
    }
    vector<bitset<2005>> Frow(n), Fcol(n);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int x;
            cin >> x;
            if (x) {
                Frow[i][j] = 1;
                Fcol[j][i] = 1;
            }
        }
    }
    vector<int> degree(n);
    for (int i = 0; i < n; i++) {
        degree[i] = Frow[i].count() + Fcol[i].count();
        if (Frow[i][i]) degree[i]--;
    }
    vector<int> facility_order(n);
    iota(facility_order.begin(), facility_order.end(), 0);
    sort(facility_order.begin(), facility_order.end(), [&](int x, int y) {
        if (degree[x] != degree[y]) return degree[x] > degree[y];
        return x < y;
    });
    vector<int> p(n, -1);
    vector<bool> used(n, false);
    for (int step = 0; step < n; step++) {
        int i = facility_order[step];
        bitset<2005> bad_first;
        bitset<2005> bad_second;
        for (int prev = 0; prev < step; prev++) {
            int k = facility_order[prev];
            if (Frow[i][k]) bad_first.set(p[k]);
            if (Fcol[i][k]) bad_second.set(p[k]);
        }
        long long best = LLONG_MAX / 2;
        int best_j = -1;
        for (int j = 0; j < n; j++) {
            if (used[j]) continue;
            size_t cnt1 = (Drow[j] & bad_first).count();
            size_t cnt2 = (Dcol[j] & bad_second).count();
            long long temp = (long long)cnt1 + (long long)cnt2;
            if (temp < best || (temp == best && j < best_j)) {
                best = temp;
                best_j = j;
            }
        }
        p[i] = best_j;
        used[best_j] = true;
    }
    for (int i = 0; i < n; i++) {
        if (i > 0) cout << " ";
        cout << p[i] + 1;
    }
    cout << "\n";
    return 0;
}