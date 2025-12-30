#include <bits/stdc++.h>
using namespace std;

vector<int> greedy_small(int n, int need) {
    vector<int> S;
    unordered_set<int> xor_set;
    for (int x = 1; x <= n && (int)S.size() < need; ++x) {
        bool ok = true;
        vector<int> new_xors;
        for (int a : S) {
            int xr = a ^ x;
            if (xor_set.count(xr)) {
                ok = false;
                break;
            }
            new_xors.push_back(xr);
        }
        if (ok) {
            for (int xr : new_xors) xor_set.insert(xr);
            S.push_back(x);
        }
    }
    return S;
}

vector<int> construct_sidonset(int M, int need) {
    vector<int> A;
    vector<bool> seen(2 * M, false);
    for (int x = 1; x < M && (int)A.size() < need; ++x) {
        bool ok = true;
        for (int a : A) {
            int xr = a ^ x;
            if (seen[xr]) {
                ok = false;
                break;
            }
        }
        if (ok) {
            for (int a : A) {
                int xr = a ^ x;
                seen[xr] = true;
            }
            A.push_back(x);
        }
    }
    return A;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;

    int m_min = (int)sqrt(n / 2.0);
    if (m_min < 0) m_min = 0;

    if (n < 64) {
        vector<int> S = greedy_small(n, m_min);
        cout << S.size() << "\n";
        for (int x : S) cout << x << " ";
        cout << "\n";
        return 0;
    }

    // find largest r such that 2^{3r} <= n
    int b = 0;
    while ((1LL << (b + 1)) <= n) ++b;
    int r = b / 3;
    int M = 1 << r;                     // M = 2^r
    // need L such that L^3 >= m_min
    int L_min = 1;
    while (L_min * L_min * L_min < m_min) ++L_min;

    if (M - 1 < L_min) {
        // fallback to greedy
        vector<int> S = greedy_small(n, m_min);
        cout << S.size() << "\n";
        for (int x : S) cout << x << " ";
        cout << "\n";
        return 0;
    }

    vector<int> A = construct_sidonset(M, L_min);
    int L = A.size();                   // L >= L_min
    vector<int> S;
    S.reserve(L * L * L);
    for (int a : A)
        for (int b : A)
            for (int c : A)
                S.push_back(a * M * M + b * M + c);

    cout << S.size() << "\n";
    for (int x : S) cout << x << " ";
    cout << "\n";

    return 0;
}