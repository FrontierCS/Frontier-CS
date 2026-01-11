#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    int b = 1;
    vector<int> distb(n + 1, -1);
    distb[b] = 0;
    for (int v = 1; v <= n; ++v) {
        if (v == b) continue;
        cout << "? " << b << " " << v << endl;
        cout.flush();
        int d;
        cin >> d;
        distb[v] = d;
    }
    int maxd = 0;
    int c = 1;
    for (int v = 1; v <= n; ++v) {
        if (distb[v] > maxd || (distb[v] == maxd && v < c)) {
            maxd = distb[v];
            c = v;
        }
    }
    int D = distb[c];
    vector<int> distc(n + 1, -1);
    distc[c] = 0;
    for (int v = 1; v <= n; ++v) {
        if (v == c) continue;
        cout << "? " << c << " " << v << endl;
        cout.flush();
        int d;
        cin >> d;
        distc[v] = d;
    }
    vector<int> attach(n + 1, -1);
    for (int x = 1; x <= n; ++x) {
        int sum = distb[x] + D - distc[x];
        if (sum % 2 != 0) {
            // error, but shouldn't happen
            attach[x] = -1;
        } else {
            attach[x] = sum / 2;
        }
    }
    vector<int> path(D + 1, 0);
    for (int x = 1; x <= n; ++x) {
        int kk = attach[x];
        if (kk >= 0 && kk <= D && distb[x] == kk) {
            path[kk] = x;
        }
    }
    vector<int> cnt(D + 1, 0);
    for (int x = 1; x <= n; ++x) {
        int kk = attach[x];
        if (kk >= 0 && kk <= D) {
            ++cnt[kk];
        }
    }
    vector<long long> ss(D + 1);
    for (int kk = 0; kk <= D; ++kk) {
        ss[kk] = cnt[kk] - 1LL;
    }
    long long cum = 0;
    int best_k = 0;
    for (int k = 0; k <= D; ++k) {
        long long left = cum;
        if (left <= (long long)n / 2) {
            best_k = k;
        }
        cum += 1LL + ss[k];
    }
    int centroid = path[best_k];
    cout << "! " << centroid << endl;
    cout.flush();
    return 0;
}