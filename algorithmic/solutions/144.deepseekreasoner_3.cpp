#include <bits/stdc++.h>
using namespace std;

pair<int, int> query(const vector<int>& indices) {
    int k = indices.size();
    cout << "0 " << k;
    for (int x : indices) cout << " " << x;
    cout << endl;
    cout.flush();
    int m1, m2;
    cin >> m1 >> m2;
    return {m1, m2};
}

int main() {
    int n;
    cin >> n;
    vector<int> all(n);
    iota(all.begin(), all.end(), 1);
    auto [L_val, R_val] = query(all);   // L_val < R_val

    // random generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Step 1: find a set A of size 4 with m2 < L_val
    vector<int> A;
    set<vector<int>> triedA;
    while (A.empty()) {
        vector<int> cand(4);
        vector<int> perm(n);
        iota(perm.begin(), perm.end(), 1);
        shuffle(perm.begin(), perm.end(), rng);
        for (int i = 0; i < 4; ++i) cand[i] = perm[i];
        sort(cand.begin(), cand.end());
        if (triedA.count(cand)) continue;
        triedA.insert(cand);
        auto [m1, m2] = query(cand);
        if (m2 < L_val) A = cand;
    }

    // Step 2: find a set B of size 4 with m1 > R_val
    vector<int> B;
    set<vector<int>> triedB;
    while (B.empty()) {
        vector<int> cand(4);
        vector<int> perm(n);
        iota(perm.begin(), perm.end(), 1);
        shuffle(perm.begin(), perm.end(), rng);
        for (int i = 0; i < 4; ++i) cand[i] = perm[i];
        sort(cand.begin(), cand.end());
        if (triedB.count(cand)) continue;
        triedB.insert(cand);
        auto [m1, m2] = query(cand);
        if (m1 > R_val) B = cand;
    }

    int iL = -1, iR = -1;

    // Step 3: verify A using B[0]
    vector<bool> goodA(4, true);
    for (int miss = 0; miss < 4; ++miss) {
        vector<int> qind;
        for (int j = 0; j < 4; ++j)
            if (j != miss) qind.push_back(A[j]);
        qind.push_back(B[0]);
        auto [m1, m2] = query(qind);
        if (m2 == L_val) {
            iL = A[miss];
            goodA[miss] = false;
        } else if (m2 == R_val) {
            iR = A[miss];
            goodA[miss] = false;
        }
        // if m2 < L_val, the missing index is < L -> keep in A
    }
    vector<int> newA;
    for (int i = 0; i < 4; ++i)
        if (goodA[i]) newA.push_back(A[i]);
    A = newA;

    // If both found, output and exit
    if (iL != -1 && iR != -1) {
        cout << "1 " << iL << " " << iR << endl;
        return 0;
    }

    // Step 4: verify B using A[0] (A is non‑empty because we removed at most two)
    vector<bool> goodB(4, true);
    for (int miss = 0; miss < 4; ++miss) {
        vector<int> qind;
        for (int j = 0; j < 4; ++j)
            if (j != miss) qind.push_back(B[j]);
        qind.push_back(A[0]);
        auto [m1, m2] = query(qind);
        if (m2 == L_val) {
            iL = B[miss];
            goodB[miss] = false;
        } else if (m2 == R_val) {
            iR = B[miss];
            goodB[miss] = false;
        } else if (m2 < L_val) {
            iL = B[miss];
            goodB[miss] = false;
        }
        // if m2 > R_val, the missing index is > R -> keep in B
    }
    vector<int> newB;
    for (int i = 0; i < 4; ++i)
        if (goodB[i]) newB.push_back(B[i]);
    B = newB;

    if (iL != -1 && iR != -1) {
        cout << "1 " << iL << " " << iR << endl;
        return 0;
    }

    // Now A has at least 2 elements (all < L), B has at least 1 element (all > R)
    int a0 = A[0], a1 = A[1];
    int b0 = B[0];

    // Step 5: classify the remaining indices
    vector<bool> used(n + 1, false);
    for (int x : A) used[x] = true;
    for (int x : B) used[x] = true;
    if (iL != -1) used[iL] = true;
    if (iR != -1) used[iR] = true;

    for (int i = 1; i <= n; ++i) {
        if (used[i]) continue;
        vector<int> qind = {i, a0, a1, b0};
        auto [m1, m2] = query(qind);
        if (m2 == L_val) {
            iL = i;
        } else if (m2 == R_val) {
            iR = i;
        }
        used[i] = true;
        if (iL != -1 && iR != -1) break;
    }

    cout << "1 " << iL << " " << iR << endl;
    return 0;
}