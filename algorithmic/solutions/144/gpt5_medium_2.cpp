#include <bits/stdc++.h>
using namespace std;

enum Type { A=0, B, C, D, E, F, UNKNOWN };

pair<int,int> do_query_excluding(int n, int i, int j) {
    vector<int> S;
    S.reserve(n-2);
    for (int idx = 1; idx <= n; ++idx) {
        if (idx == i || idx == j) continue;
        S.push_back(idx);
    }
    cout << 0 << " " << (int)S.size();
    for (int x : S) cout << " " << x;
    cout << endl;
    cout.flush();
    int m1, m2;
    if (!(cin >> m1 >> m2)) {
        exit(0);
    }
    if (m1 == -1 && m2 == -1) exit(0);
    return {m1, m2};
}

Type classify_pair(int n, pair<int,int> res) {
    int m1 = res.first, m2 = res.second;
    int t1 = n/2;
    int t2 = t1 + 1;
    if (m1 == t1 && m2 == t2) return A;
    if (m1 == t1-1 && m2 == t2) return B;
    if (m1 == t1 && m2 == t2+1) return C;
    if (m1 == t2 && m2 == t2+1) return D;
    if (m1 == t1-1 && m2 == t1) return E;
    if (m1 == t1-1 && m2 == t2+1) return F;
    return UNKNOWN;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    int r = 1;
    vector<Type> typ(n+1, UNKNOWN);
    vector<int> cnt(6, 0);
    vector<int> idxOf(6, -1);

    for (int i = 1; i <= n; ++i) {
        if (i == r) continue;
        auto res = do_query_excluding(n, i, r);
        Type t = classify_pair(n, res);
        typ[i] = t;
        if (t != UNKNOWN) {
            cnt[(int)t]++;
            idxOf[(int)t] = i;
        }
    }

    int idxM1 = -1, idxM2 = -1;

    if (cnt[F] > 0) {
        if (cnt[B] > 0) {
            // r is M1
            idxM1 = r;
            idxM2 = idxOf[F];
        } else {
            // r is M2
            idxM2 = r;
            idxM1 = idxOf[F];
        }
    } else {
        if (cnt[C] > 0) {
            // r is L; unique C is M2
            idxM2 = idxOf[C];
            int s = idxM2;
            // second sweep to find M1 as unique F
            for (int i = 1; i <= n; ++i) {
                if (i == s) continue;
                auto res = do_query_excluding(n, i, s);
                Type t = classify_pair(n, res);
                if (t == F) {
                    idxM1 = i;
                    break;
                }
            }
        } else {
            // r is H; unique B is M1
            idxM1 = idxOf[B];
            int s = idxM1;
            // second sweep to find M2 as unique F
            for (int i = 1; i <= n; ++i) {
                if (i == s) continue;
                auto res = do_query_excluding(n, i, s);
                Type t = classify_pair(n, res);
                if (t == F) {
                    idxM2 = i;
                    break;
                }
            }
        }
    }

    if (idxM1 == -1 || idxM2 == -1) {
        // Fallback (should not happen); just exit
        // to avoid infinite interaction
        cout << 1 << " " << 1 << " " << 2 << endl;
        cout.flush();
        return 0;
    }

    cout << 1 << " " << idxM1 << " " << idxM2 << endl;
    cout.flush();
    return 0;
}