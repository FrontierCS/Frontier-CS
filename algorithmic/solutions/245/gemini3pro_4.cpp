#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

// Wrapper for queries to handle interaction
int query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); // Error or end
    return res;
}

void answer(int x) {
    cout << "! " << x << endl;
}

void solve() {
    int n;
    if (!(cin >> n)) exit(0);
    
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);

    // Random generator
    mt19937 rng(1337);

    while (candidates.size() > 1) {
        if (candidates.size() == 2) {
            int u = candidates[0];
            int v = candidates[1];
            int q1 = query(u, v);
            int q2 = query(v, u);
            if (q1 != q2) {
                // One is Impostor. Check u against a third person w.
                // Since n >= 3, find w != u and w != v.
                int w = 1;
                while (w == u || w == v) w++;
                
                int q3 = query(u, w);
                int q4 = query(w, u);
                if (q3 != q4) {
                    answer(u);
                } else {
                    answer(v);
                }
            } else {
                // Should not happen if Impostor is in candidates.
                // Just guess one to avoid infinite loop if something went wrong.
                answer(u); 
            }
            return;
        }

        // Pick pivot
        int p_idx = std::uniform_int_distribution<int>(0, candidates.size() - 1)(rng);
        int p = candidates[p_idx];
        
        vector<int> S, D;
        for (int x : candidates) {
            if (x == p) continue;
            if (query(p, x) == 1) {
                S.push_back(x);
            } else {
                D.push_back(x);
            }
        }

        // We verify the smaller set to minimize queries
        bool checkS = (S.size() <= D.size());
        
        if (checkS) {
            if (S.empty()) {
                candidates = D; // I must be in D
                continue;
            }
            vector<int> ones, zeros;
            for (int x : S) {
                if (query(x, p) == 1) ones.push_back(x);
                else zeros.push_back(x);
            }
            
            if (zeros.empty()) {
                // All 1s. S is consistent/pure. I is in D.
                candidates = D;
            } else if (zeros.size() > 1) {
                // Too many inconsistencies. p is Impostor.
                answer(p);
                return;
            } else {
                // Exactly one 0. 
                // Could be p=K, x=I (I->K is 0) -> x is I.
                // Or p=I, x=L (L->I is 0) -> p is I.
                // Distinguish: if ones > 0, then p is supported by others, so p != I.
                if (!ones.empty()) {
                    answer(zeros[0]);
                    return;
                } else {
                    // S has size 1. Ambiguous.
                    int x = zeros[0];
                    // Pick z from D
                    if (D.empty()) {
                        // Should not happen if n >= 3, as S size 1 => D size n-2 >= 1
                        answer(x); // Fallback
                        return;
                    }
                    int z = D[0];
                    int q_xz = query(x, z);
                    int q_zx = query(z, x);
                    if (q_xz != q_zx) answer(x);
                    else answer(p);
                    return;
                }
            }
        } else {
            if (D.empty()) {
                candidates = S;
                continue;
            }
            vector<int> ones, zeros;
            for (int x : D) {
                if (query(x, p) == 1) ones.push_back(x);
                else zeros.push_back(x);
            }
            
            if (ones.empty()) {
                // All 0s. D is consistent/pure. I is in S.
                candidates = S;
            } else if (ones.size() > 1) {
                // Too many inconsistencies. p is Impostor.
                answer(p);
                return;
            } else {
                // Exactly one 1.
                // Could be p=L, x=I (I->L is 1) -> x is I.
                // Or p=I, x=K (K->I is 1) -> p is I.
                if (!zeros.empty()) {
                    answer(ones[0]);
                    return;
                } else {
                    // D has size 1. Ambiguous.
                    int x = ones[0];
                    if (S.empty()) {
                        answer(x);
                        return;
                    }
                    int z = S[0];
                    int q_xz = query(x, z);
                    int q_zx = query(z, x);
                    if (q_xz != q_zx) answer(x);
                    else answer(p);
                    return;
                }
            }
        }
    }
    
    answer(candidates[0]);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}