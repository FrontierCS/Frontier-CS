#include <bits/stdc++.h>
using namespace std;

int query(int x) {
    cout << "? " << x << endl;
    int r;
    cin >> r;
    return r;
}

void answer(int a, int b) {
    cout << "! " << a << " " << b << endl;
}

// match returns (unmatched in L, unmatched in R)
pair<vector<int>, vector<int>> match(vector<int> L, vector<int> R) {
    if (L.empty() || R.empty()) {
        return {L, R};
    }
    if (L.size() == 1 && R.size() == 1) {
        // test if they are partners
        int d1 = query(L[0]);
        int d2 = query(R[0]);
        if (d2 == d1) {
            // partners
            answer(L[0], R[0]);
            // remove both
            query(L[0]);
            query(R[0]);
            return {{}, {}};
        } else {
            // not partners
            query(L[0]); // remove L[0]
            query(R[0]); // remove R[0]
            return {L, R};
        }
    }
    // split L into two halves
    int m = L.size();
    vector<int> L1(L.begin(), L.begin() + m/2);
    vector<int> L2(L.begin() + m/2, L.end());
    
    // insert L1
    for (int x : L1) query(x);
    int d = L1.size();
    vector<int> R1, R2;
    for (int r : R) {
        int new_d = query(r);
        if (new_d == d) {
            R1.push_back(r);
        } else {
            R2.push_back(r);
        }
        d = new_d;
    }
    // now device contains L1 ∪ R
    // remove L1
    for (int x : L1) query(x);
    // remove R
    for (int r : R) query(r);
    // device empty now
    
    auto [L1_rem, R1_rem] = match(L1, R1);
    auto [L2_rem, R2_rem] = match(L2, R2);
    
    vector<int> L_rem = L1_rem;
    L_rem.insert(L_rem.end(), L2_rem.begin(), L2_rem.end());
    vector<int> R_rem = R1_rem;
    R_rem.insert(R_rem.end(), R2_rem.begin(), R2_rem.end());
    return {L_rem, R_rem};
}

// process set v, output pairs inside v, return indices in v that pair outside v
vector<int> process(vector<int> v) {
    if (v.size() <= 1) {
        return v;
    }
    if (v.size() == 2) {
        // test if they are partners
        int d1 = query(v[0]);
        int d2 = query(v[1]);
        if (d2 == d1) {
            answer(v[0], v[1]);
            // remove both
            query(v[0]);
            query(v[1]);
            return {};
        } else {
            // not partners
            query(v[0]);
            query(v[1]);
            return v;
        }
    }
    int mid = v.size() / 2;
    vector<int> left(v.begin(), v.begin() + mid);
    vector<int> right(v.begin() + mid, v.end());
    vector<int> L = process(left);
    vector<int> R = process(right);
    auto [L_rem, R_rem] = match(L, R);
    vector<int> unmatched = L_rem;
    unmatched.insert(unmatched.end(), R_rem.begin(), R_rem.end());
    return unmatched;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int N;
    cin >> N;
    vector<int> all(2*N);
    iota(all.begin(), all.end(), 1);
    process(all);
    return 0;
}