#include <bits/stdc++.h>
using namespace std;

static int n;
static int query_cnt = 0;

pair<int,int> query_complement(int a, int b) {
    ++query_cnt;
    cout << "0 " << (n - 2);
    for (int i = 1; i <= n; i++) {
        if (i == a || i == b) continue;
        cout << " " << i;
    }
    cout << endl;

    int x, y;
    if (!(cin >> x >> y)) exit(0);
    if (x == -1 && y == -1) exit(0);
    return {x, y};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    int m = n / 2;

    int s = m + 3;
    if (s > n) s = n;
    vector<int> S;
    for (int i = 1; i <= s; i++) S.push_back(i);

    int u = -1, v = -1;
    // Find u,v such that removing them yields (m, m+1) => u and v are opposite sides (non-medians).
    for (int cand : S) {
        bool found = false;
        for (int other : S) {
            if (other == cand) continue;
            auto res = query_complement(cand, other);
            if (res.first == m && res.second == m + 1) {
                u = cand; v = other;
                found = true;
                break;
            }
        }
        if (found) break;
    }

    if (u == -1 || v == -1) {
        // Fallback (shouldn't happen): brute within query limit
        for (int i = 1; i <= n && u == -1; i++) {
            for (int j = i + 1; j <= n; j++) {
                auto res = query_complement(i, j);
                if (res.first == m && res.second == m + 1) {
                    u = i; v = j;
                    break;
                }
            }
        }
    }

    int L = -1, H = -1;
    // Determine which one is low (<m) and which one is high (>m+1).
    bool oriented = false;
    for (int w : S) {
        if (w == u || w == v) continue;
        auto res = query_complement(u, w);
        if (res.first == m && res.second == m + 1) continue;
        if (res.first < m) { // u is high
            H = u; L = v;
        } else {
            L = u; H = v;
        }
        oriented = true;
        break;
    }
    if (!oriented) {
        for (int w = 1; w <= n; w++) {
            if (w == u || w == v) continue;
            auto res = query_complement(u, w);
            if (res.first == m && res.second == m + 1) continue;
            if (res.first < m) { H = u; L = v; }
            else { L = u; H = v; }
            oriented = true;
            break;
        }
    }

    int idxB = -1; // value m+1
    for (int x = 1; x <= n; x++) {
        if (x == L || x == H) continue;
        auto res = query_complement(L, x);
        if (res.first == m && res.second == m + 2) {
            idxB = x;
            break;
        }
    }

    int idxA = -1; // value m
    for (int x = 1; x <= n; x++) {
        if (x == L || x == H || x == idxB) continue;
        auto res = query_complement(H, x);
        if (res.first == m - 1 && res.second == m + 1) {
            idxA = x;
            break;
        }
    }

    if (idxA == -1 || idxB == -1) exit(0);

    cout << "1 " << idxA << " " << idxB << endl;
    return 0;
}